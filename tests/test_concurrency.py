"""Deterministic Stop-priority tests: no hardware or network I/O."""
import pathlib
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import edge_dashboard as dashboard


class ConcurrentStopTests(unittest.TestCase):
    def setUp(self):
        self.engine = dashboard.Engine("127.0.0.1", simulate=True)

    def tearDown(self):
        self.engine.shutdown()

    def _stop_during_validation(self, launch):
        entered, proceed = threading.Event(), threading.Event()
        results = {}
        def blocked_validation():
            entered.set()
            if not proceed.wait(3):
                raise AssertionError("test timed out waiting for validation release")

        def run_start():
            try:
                results['result'] = launch()
            except RuntimeError as exc:
                results['error'] = str(exc)
        with patch.object(self.engine, '_require_edge2', side_effect=blocked_validation):
            worker = threading.Thread(target=run_start)
            worker.start()
            try:
                self.assertTrue(entered.wait(2), "Start never reached validation")
                self.engine.stop("Explicit Stop while Start pending")
            finally:
                proceed.set()
                worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
        self.assertFalse(self.engine.status()['running'], f"STOP lost to Start: {results}")
        self.assertIn('cancel', results.get('error', '').lower(), f"Start not aborted: {results}")

    def test_stop_during_start_validation_does_not_restart_motors(self):
        self._stop_during_validation(lambda: self.engine.start({"mode": "manual", "max": 5, "motor1": 5, "motor2": 5}))

    def test_stop_during_motor_test_validation_does_not_restart_motors(self):
        self._stop_during_validation(self.engine.test)

    def test_stop_during_pattern_switch_validation_does_not_restart_motors(self):
        # Exercise the internal Stop("Switching patterns") path, which must
        # never mask a separate explicit Stop arriving during validation.
        self.engine.start({"mode": "manual", "max": 5, "motor1": 4, "motor2": 2})
        self._stop_during_validation(lambda: self.engine.start({"mode": "wave", "max": 5}))

    def test_stop_during_pattern_to_motor_test_switch_never_restarts(self):
        self.engine.start({"mode": "manual", "max": 5, "motor1": 4, "motor2": 2})
        self._stop_during_validation(self.engine.test)

    def test_new_explicit_start_after_stop_is_allowed(self):
        self.engine.start({"mode": "wave", "max": 5})
        self.engine.stop("Explicit Stop")
        self.assertFalse(self.engine.status()["running"])
        started = self.engine.start({"mode": "manual", "max": 5, "motor1": 4, "motor2": 0})
        self.assertTrue(started["running"])


if __name__ == '__main__':
    unittest.main()
