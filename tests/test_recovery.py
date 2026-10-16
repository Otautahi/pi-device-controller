"""Deterministic offline tests for Stop reconciliation after Wi-Fi/Bluetooth loss.

No real device/network activity; a fake Lovense Game Mode API supplies answers.
"""
import json
import pathlib
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import edge_dashboard as dashboard


class FakeLovense:
    def __init__(self, failure="bluetooth"):
        self.connected = True
        self.phone_online = True
        self.commands = []
        self.guard = threading.Lock()
        self.failure = failure
        self.reject_stops = False

    def api(self, payload):
        with self.guard:
            command = payload["command"]
            action = payload.get("action", "")
            self.commands.append((command, action, self.connected, self.phone_online))
            if not self.phone_online:
                raise RuntimeError("Cannot reach Lovense Remote (mock Wi-Fi loss)")
            if command == "GetToys":
                data = {"id": {"name": "edge", "status": "1" if self.connected else "0"}}
                return {"code": 200, "data": {"toys": json.dumps(data)}}
            if not self.connected or (action == "Stop" and self.reject_stops):
                raise RuntimeError("Lovense returned: {'code': 402, 'type': 'OK'}")
            return {"code": 200, "type": "OK"}

    def messages(self):
        with self.guard:
            return list(self.commands)


class RecoveryTests(unittest.TestCase):
    @staticmethod
    def wait_for(predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(.025)
        return bool(predicate())

    def setUp(self):
        self.fake = FakeLovense()
        self.engine = dashboard.Engine("127.0.0.1", simulate=False)
        self.api = patch.object(self.engine, "_api", side_effect=self.fake.api)
        self.api.start()

    def tearDown(self):
        self.engine.shutdown()
        self.api.stop()

    def test_402_latches_stop_and_retries_when_bluetooth_returns(self):
        self.engine.start({"mode": "manual", "motor1": 3, "motor2": 2, "max": 5})
        self.assertTrue(self.wait_for(lambda: any(c[1].startswith("Vibrate1:") for c in self.fake.messages())))
        self.fake.connected = False
        self.assertTrue(self.wait_for(lambda: self.engine.status()["faultLatched"]))
        s = self.engine.status()
        self.assertFalse(s["running"])
        self.assertTrue(s["stopPending"])
        self.assertIn("STOP NOT DELIVERED", s["message"])
        with self.assertRaisesRegex(RuntimeError, "fault locked|fault.*lock|recovery incomplete"):
            self.engine.start({"mode": "wave"})
        with self.assertRaisesRegex(RuntimeError, "fault locked|recovery incomplete"):
            self.engine.test()
        with self.assertRaisesRegex(RuntimeError, "recovery incomplete"):
            self.engine.acknowledge_fault()
        before_reconnect = len(self.fake.messages())
        self.fake.connected = True
        self.engine.recovery_wake.set()
        self.assertTrue(self.wait_for(lambda: not self.engine.status()["stopPending"], timeout=6))
        sent = self.fake.messages()[before_reconnect:]
        stops = [a for cmd, a, connected, online in sent if cmd == "Function" and a == "Stop" and connected and online]
        non_stops = [a for cmd, a, connected, online in sent if cmd == "Function" and a != "Stop"]
        self.assertGreaterEqual(len(stops), 3)
        self.assertFalse(non_stops, f"A stale vibration command ran after reconnection: {non_stops}")
        self.assertFalse(self.engine.status()["running"])
        self.assertTrue(self.engine.status()["faultLatched"])
        self.assertEqual(self.engine.status()["stopAcks"], 3)
        self.engine.acknowledge_fault()
        self.assertFalse(self.engine.status()["faultLatched"])

    def test_wifi_loss_latches_and_recovers_after_phone_comes_back(self):
        self.engine.start({"mode": "manual", "max": 5, "motor1": 3, "motor2": 2})
        self.assertTrue(self.wait_for(lambda: self.engine.status()["sessionCommands"] > 0))
        self.fake.phone_online = False
        self.assertTrue(self.wait_for(lambda: self.engine.status()["faultLatched"]))
        self.assertTrue(self.engine.status()["stopPending"])
        self.fake.phone_online = True
        self.engine.recovery_wake.set()
        self.assertTrue(self.wait_for(lambda: not self.engine.status()["stopPending"], timeout=6))
        self.assertFalse(self.engine.status()["running"])
        self.assertTrue(self.engine.status()["faultLatched"])

    def test_normal_stop_does_not_lock_successful_session(self):
        self.engine.start({"mode": "wave"})
        self.engine.stop("Manual Stop")
        self.assertFalse(self.engine.status()["faultLatched"])
        self.assertFalse(self.engine.status()["stopPending"])

    def test_failed_manual_stop_while_idle_is_also_retried(self):
        self.fake.connected = False
        with self.assertRaisesRegex(RuntimeError, "402"):
            self.engine.stop()
        self.assertTrue(self.engine.status()["faultLatched"])
        self.fake.connected = True
        self.engine.recovery_wake.set()
        self.assertTrue(self.wait_for(lambda: not self.engine.status()["stopPending"], timeout=6))
        self.assertFalse(self.engine.status()["running"])

    def test_phone_online_but_bluetooth_off_never_counts_stop_ack(self):
        self.engine.start({"mode": "wave"})
        self.fake.phone_online = False
        self.assertTrue(self.wait_for(lambda: self.engine.status()["faultLatched"]))
        self.fake.phone_online = True
        self.fake.connected = False
        time.sleep(1.3)
        s = self.engine.status()
        self.assertTrue(s["stopPending"])
        self.assertEqual(s["stopAcks"], 0)
        self.fake.connected = True
        self.engine.recovery_wake.set()
        self.assertTrue(self.wait_for(lambda: not self.engine.status()["stopPending"], 6))

    def test_connected_phone_rejecting_stop_does_not_clear_fault(self):
        self.engine.start({"mode": "wave"})
        self.fake.reject_stops = True
        with self.assertRaisesRegex(RuntimeError, "402"):
            self.engine.stop("Test Stop failure")
        self.assertTrue(self.engine.status()["faultLatched"])
        time.sleep(1.2)
        self.assertTrue(self.engine.status()["stopPending"])
        with self.assertRaises(RuntimeError):
            self.engine.acknowledge_fault()
        self.fake.reject_stops = False
        self.engine.recovery_wake.set()
        self.assertTrue(self.wait_for(lambda: not self.engine.status()["stopPending"], 6))

    def test_acknowledge_no_fault_never_deadlocks(self):
        self.assertFalse(self.engine.acknowledge_fault()["faultLatched"])

    def test_failed_stop_keeps_old_generation_blocked(self):
        self.engine.start({"mode": "manual", "motor1": 5, "motor2": 5, "max": 5})
        with self.engine.state_lock:
            gen = self.engine.generation
        self.fake.connected = False
        with self.assertRaises(RuntimeError):
            self.engine.stop("Bluetooth lost", fault=True)
        self.fake.connected = True
        self.assertFalse(self.engine._send_levels(gen, 5, 5))


if __name__ == "__main__":
    unittest.main()
