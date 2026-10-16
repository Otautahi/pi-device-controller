#!/usr/bin/env python3
"""PulseDirector v4.5 LAN Edition: independent Edge 2 controller for a trusted local network.

Requires Lovense Remote Game Mode on a phone connected to the same LAN.
Standard library only; local Game Mode communications only.
"""
import argparse
import ipaddress
import hmac
import json
import math
import os
from pathlib import Path
import random
from edge2_director import AutonomousDirector, STYLES, FLOWS
import secrets
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODES = {"autonomous", "wave", "pulse", "alternate", "chase", "sync", "ramp", "random",
         "anchor", "heartbeat", "orbit", "cascade", "flutter", "tide",
         "motor1", "motor2", "manual", "test", "echo", "drift", "steps", "ripple"}
RANDOM_MODES = ("wave", "pulse", "alternate", "chase", "sync", "ramp",
                "anchor", "heartbeat", "orbit", "cascade", "flutter", "tide", "echo", "drift", "steps", "ripple")
KEY_FILE = Path(__file__).resolve().parent / ".edge_dashboard_key"


def limited_number(value, low, high, integral=False):
    try:
        val = float(value)
        if not math.isfinite(val):
            raise ValueError("Not a finite number")
        val = min(high, max(low, val))
        return int(round(val)) if integral else val
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"Expected a number between {low} and {high}") from None


class Engine:
    def __init__(self, phone, simulate=False):
        self.url = f"http://{phone}:20010/command"
        self.simulate = simulate
        self.state_lock = threading.Lock()
        self.io_lock = threading.Lock()
        self.wake = threading.Event()
        self.close = threading.Event()
        self.mode = "idle"
        self.generation = 0
        # Stop has priority over an in-flight Start or motor Test request.
        self.stop_epoch = 0
        self.started = 0.0
        self.end = 0.0
        self.max_level = 10
        self.speed = 3
        self.minutes = 5.0
        self.motor1 = 4
        self.motor2 = 4
        self.motor2_support = 65  # Pattern Motor 2 strength as % of its programmed peak
        self.display1 = 0
        self.display2 = 0
        self.message = "Ready — connect your Edge 2 in Lovense Remote."
        self.random_modes = []
        self.director = None
        self.director_style = "confident"
        self.director_surprise = 4
        self.director_flow = "driving"
        # Reported by Lovense Remote, not measured directly by this program.
        self.battery = None
        self.toy_connected = None
        self.device_name = "Edge 2"
        self.last_telemetry = None
        self.last_device_error = ""
        # A failed Stop is NOT a physical Stop. Hold a fault until connected
        # again and multiple Stop requests have been acknowledged by the phone.
        self.fault_latched = False
        self.fault_reason = ""
        self.stop_pending = False
        self.stop_acks = 0
        self.stop_attempts = 0
        self.last_stop_error = ""
        self.recovery_wake = threading.Event()
        self.session_commands = 0
        self.total_commands = 0
        self.worker = threading.Thread(target=self._loop, name="edge-pattern-worker", daemon=True)
        self.telemetry_worker = threading.Thread(target=self._telemetry_loop, name="edge-telemetry", daemon=True)
        self.recovery_worker = threading.Thread(target=self._recovery_loop, name="edge-stop-recovery", daemon=True)
        self.worker.start()
        self.telemetry_worker.start()
        self.recovery_worker.start()

    def _api(self, payload):
        if self.simulate:
            return {"code": 200, "type": "ok", "simulated": True}
        req = Request(self.url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json", "X-platform": "Pi-Edge-Dashboard"},
                      method="POST")
        try:
            with urlopen(req, timeout=2.5) as response:
                result = json.load(response)
        except (URLError, HTTPError, OSError, TimeoutError) as exc:
            raise RuntimeError(f"Cannot reach Lovense Remote ({exc}). Check Game Mode and phone Wi-Fi.") from exc
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError("Lovense Remote returned an unexpected response") from exc
        if result.get("code") != 200:
            raise RuntimeError(f"Lovense returned: {result}")
        return result

    def _send_levels(self, gen, a, b):
        # Serialise with STOP, and recheck after waiting on I/O lock so a
        # previous generation cannot switch the toy back on after STOP.
        with self.io_lock:
            with self.state_lock:
                if gen != self.generation or self.mode == "idle" or self.fault_latched:
                    return False
                if time.monotonic() >= self.end:
                    return False
            self._api({"command": "Function", "action": f"Vibrate1:{a},Vibrate2:{b}",
                       "timeSec": 2, "stopPrevious": 1, "apiVer": 1})
            with self.state_lock:
                if gen == self.generation:
                    self.display1 = a
                    self.display2 = b
                    self.session_commands += 1
                    self.total_commands += 1
        return True

    def _send_stop(self):
        with self.io_lock:
            return self._api({"command": "Function", "action": "Stop", "timeSec": 0,
                              "stopPrevious": 1, "apiVer": 1})

    def _set_idle(self, why, cancel_pending=True):
        with self.state_lock:
            self.generation += 1
            if cancel_pending:
                self.stop_epoch += 1
            self.mode = "idle"
            self.end = 0.0
            self.display1 = self.display2 = 0
            self.message = why
            self.wake.set()

    def stop(self, why="Stopped", fault=False, cancel_pending=True):
        """Stop immediately if reachable; remember a failed Stop for recovery.

        A 200 response acknowledges the phone API, NOT the toy's physical state.
        In particular, Stop attempted during Bluetooth loss can return 402.
        """
        self._set_idle(why, cancel_pending=cancel_pending)
        if fault:
            with self.state_lock:
                self.fault_latched = True
                self.fault_reason = why
                self.stop_pending = True
                self.stop_acks = 0
        try:
            self._send_stop()
        except RuntimeError as exc:
            with self.state_lock:
                self.fault_latched = True
                self.fault_reason = self.fault_reason or why
                self.stop_pending = True
                self.stop_acks = 0
                self.last_stop_error = str(exc)
                self.message = "Stop command failed: " + str(exc) + ". STOP NOT DELIVERED; physical state UNKNOWN. Check toy."
            self.recovery_wake.set()
            raise
        with self.state_lock:
            self.last_stop_error = ""
            if self.fault_latched:
                # A fault always needs reconciliation, even if a single Stop
                # was accepted. A later successful API call is not proof that
                # the Bluetooth device stopped physically.
                self.stop_pending = True
                self.stop_acks = min(self.stop_acks + 1, 2)
                self.message = "Connection fault — verifying Stop on reconnect; physical state unknown."
                self.recovery_wake.set()
        return self.status()

    def acknowledge_fault(self):
        """Explicit re-arm only after repeated successful STOP acknowledgments."""
        with self.state_lock:
            if self.mode != "idle" or self.stop_pending:
                raise RuntimeError("Stop recovery incomplete; keep device physically off")
            if self.fault_latched:
                self.fault_latched = False
                self.fault_reason = ""
                self.last_stop_error = ""
                self.message = "Fault acknowledged. Physical motor state was not independently measured."
        return self.status()

    def _recovery_loop(self):
        """Once per second, reconcile a failed Stop when LAN/Bluetooth returns.

        No Start is possible while the fault is latched. Do not confuse an
        accepted Stop response with a physical guarantee of motor inactivity.
        """
        while not self.close.is_set():
            with self.state_lock:
                pending = self.stop_pending
            if pending:
                try:
                    # GETTOYS must report one real connected Edge 2; a live
                    # phone with Bluetooth disabled is not sufficient.
                    ready = self.refresh_toys()["toyConnected"]
                    if ready:
                        self._send_stop()
                        with self.state_lock:
                            if self.stop_pending:
                                self.stop_attempts += 1
                                self.stop_acks += 1
                                self.last_stop_error = ""
                                if self.stop_acks >= 3:
                                    self.stop_pending = False
                                    self.message = ("Recovery STOP accepted by Lovense Remote; "
                                                    "physically check toy and acknowledge fault before starting.")
                                else:
                                    self.message = "Recovery Stop sent; confirming after reconnection."
                except RuntimeError as exc:
                    with self.state_lock:
                        self.stop_acks = 0
                        self.last_stop_error = str(exc)
                        self.message = "STOP NOT DELIVERED; device state UNKNOWN. " + str(exc)
            self.recovery_wake.wait(1.0)
            self.recovery_wake.clear()

    def start(self, body):
        if not isinstance(body, dict):
            raise ValueError("Invalid settings")
        mode = body.get("mode", "wave")
        if mode not in MODES or mode == "test":
            raise ValueError("Unknown pattern mode")
        max_level = limited_number(body.get("max", 10), 1, 20, True)
        speed = limited_number(body.get("speed", 3), 1, 5, True)
        minutes = limited_number(body.get("minutes", 5), .25, 20)
        m1 = limited_number(body.get("motor1", 4), 0, 20, True)
        m2 = limited_number(body.get("motor2", 4), 0, 20, True)
        support = limited_number(body.get("support", 65), 0, 100, True)
        style = body.get("style", "confident")
        if not isinstance(style, str) or style not in STYLES:
            raise ValueError("Invalid Director style")
        flow = body.get("flow", "driving")
        if not isinstance(flow, str) or flow not in FLOWS:
            raise ValueError("Invalid Director session flow")
        surprise = limited_number(body.get("surprise", 4), 0, 6, True)
        if not 1 <= surprise <= 5:
            raise ValueError("Surprise must be between 1 and 5")
        # No reactivation while a connection/Stop error remains latched.
        with self.state_lock:
            if self.fault_latched or self.close.is_set():
                raise RuntimeError("Connection fault locked or shutting down: cannot start")
            request_stop_epoch = self.stop_epoch
            already_running = self.mode != "idle"
        if already_running:
            # Internal mode switch must not hide a *separate* Stop request.
            with self.state_lock:
                if self.stop_epoch != request_stop_epoch:
                    raise RuntimeError("Start cancelled by STOP")
            self.stop("Switching patterns", cancel_pending=False)
        self._require_edge2()
        with self.state_lock:
            if self.stop_epoch != request_stop_epoch or self.close.is_set():
                raise RuntimeError("Start cancelled by STOP")
            if self.fault_latched:
                raise RuntimeError("Connection fault locked: cannot start")
            self.generation += 1
            self.mode = mode
            self.max_level = max_level
            self.speed = speed
            self.minutes = minutes
            self.motor1 = min(m1, max_level)
            self.motor2 = min(m2, max_level)
            self.motor2_support = support
            self.director_style = style
            self.director_surprise = surprise
            self.director_flow = flow
            self.director = AutonomousDirector(style=style, surprise=surprise, flow=flow) if mode == "autonomous" else None
            self.started = time.monotonic()
            self.end = self.started + minutes * 60
            self.display1 = self.display2 = 0
            choices = []
            for _ in range(300):
                options = [item for item in RANDOM_MODES if item not in choices[-3:]]
                choices.append(random.choice(options))
            self.random_modes = choices
            self.session_commands = 0
            self.message = ("Autonomous Director · " + style.title() if mode == "autonomous"
                            else "Running: " + mode.title())
            self.wake.set()
        return self.status()

    def test(self):
        # Tests separate motor commands; a device without support will error.
        with self.state_lock:
            if self.fault_latched or self.close.is_set():
                raise RuntimeError("Connection fault locked or shutting down: cannot test motors")
            request_stop_epoch = self.stop_epoch
            already_running = self.mode != "idle"
        if already_running:
            with self.state_lock:
                if self.stop_epoch != request_stop_epoch:
                    raise RuntimeError("Motor test cancelled by STOP")
            self.stop("Starting motor test", cancel_pending=False)
        self._require_edge2()
        with self.state_lock:
            if self.stop_epoch != request_stop_epoch or self.close.is_set():
                raise RuntimeError("Motor test cancelled by STOP")
            if self.fault_latched:
                raise RuntimeError("Connection fault locked: cannot test motors")
            self.generation += 1
            self.mode = "test"
            self.max_level = 5
            self.speed = 3
            self.started = time.monotonic()
            self.end = self.started + 7.0
            self.display1 = self.display2 = 0
            self.session_commands = 0
            self.message = "Testing motor 1, motor 2, then both (about 7 seconds)"
            self.wake.set()
        return self.status()

    @staticmethod
    def _extract_toy(data):
        """Select only ONE connected Edge 2 from Game Mode's GetToys response.

        Accept both native objects and the API's JSON-in-a-string wrappers.
        Do not silently choose the first connected device when several are present.
        """
        info = data.get("data", {})
        for _ in range(3):
            if isinstance(info, str):
                try:
                    info = json.loads(info)
                except (ValueError, TypeError):
                    return None, "Unrecognised GetToys response"
            if isinstance(info, dict) and "toys" in info:
                info = info["toys"]
            else:
                break
        if isinstance(info, dict):
            if "battery" in info or "status" in info or "name" in info:
                devices = [info]
            else:
                devices = list(info.values())
        elif isinstance(info, list):
            devices = info
        else:
            devices = []
        connected = [item for item in devices if isinstance(item, dict)
                     and str(item.get("status", "")).lower() in ("1", "true", "connected")]
        if not connected:
            return None, "No connected device reported"
        if len(connected) != 1:
            return None, "Multiple connected devices reported; disconnect others"
        toy = connected[0]
        # Prefer hardware-reported model over a user-supplied nickname.
        model = str(toy.get("name") or toy.get("model") or "").lower().strip()
        model = "".join(ch for ch in model if ch.isalnum())
        if model not in ("edge", "edge2"):
            return None, "Connected device is not confirmed as an Edge 2"
        return toy, ""

    def _require_edge2(self):
        status = self.refresh_toys()
        if status["toyConnected"] is not True:
            raise RuntimeError(status["lastDeviceError"] or "Edge 2 not ready")

    def refresh_toys(self):
        if self.simulate:
            data = {"code": 200, "data": {"toys": json.dumps({
                "simulated": {"name": "edge", "battery": 72, "status": "1"}})}}
        else:
            with self.io_lock:
                data = self._api({"command": "GetToys"})
        toy, error = self._extract_toy(data)
        with self.state_lock:
            self.last_telemetry = time.monotonic()
            if toy is None:
                self.toy_connected = False
                self.last_device_error = error
                self.battery = None
            else:
                self.toy_connected = True
                raw_battery = toy.get("battery")
                try:
                    pct = int(raw_battery)
                    self.battery = pct if 0 <= pct <= 100 else None
                except (ValueError, TypeError):
                    self.battery = None
                self.device_name = "Edge 2"
                self.last_device_error = ""
        return self.status()

    def _telemetry_loop(self):
        # Query while active about every 2 seconds to detect silent Bluetooth
        # loss; poll more slowly when idle. The motor worker also detects 402.
        if self.close.wait(.5):
            return
        while not self.close.is_set():
            try:
                status = self.refresh_toys()
            except RuntimeError as exc:
                with self.state_lock:
                    self.toy_connected = False
                    self.last_telemetry = time.monotonic()
                    self.last_device_error = str(exc)
                    status = {"toyConnected": False, "running": self.mode != "idle"}
            if status["toyConnected"] is False and status["running"] and not self.close.is_set():
                try:
                    self.stop("Edge 2 disconnected or not verified; session stopped", fault=True)
                except RuntimeError:
                    pass
            with self.state_lock:
                active = self.mode != "idle"
            self.close.wait(2 if active else 10)

    def status(self):
        with self.state_lock:
            now = time.monotonic()
            left = max(0, self.end - now) if self.mode != "idle" else 0
            elapsed = max(0, now - self.started) if self.mode != "idle" else 0
            freshness = int(now - self.last_telemetry) if self.last_telemetry is not None else None
            director_state = (self.director.snapshot(elapsed) if self.mode == "autonomous" and self.director else None)
            decisions = director_state["decisions"] if director_state else 0
            return {"mode": self.mode, "motor1": self.display1, "motor2": self.display2,
                    "directorStyle": self.director_style, "directorSurprise": self.director_surprise,
                    "directorDecisions": decisions, "directorFlow": self.director_flow,
                    "directorScene": director_state["scene"] if director_state else None,
                    "directorPhase": director_state["phase"] if director_state else None,
                    "directorEnergy": director_state["energy"] if director_state else 0,
                    "directorIntent": director_state["intent"] if director_state else "",
                    "directorReprises": director_state["reprises"] if director_state else 0,
                    "directorSceneSecondsLeft": director_state["sceneSecondsLeft"] if director_state else 0,
                    "sessionProgress": min(100, max(0, round(100 * elapsed / max(1, self.minutes * 60)))) if self.mode != "idle" else 0,
                    "secondsLeft": int(math.ceil(left)), "elapsedSeconds": int(elapsed),
                    "running": self.mode != "idle", "max": self.max_level,
                    "speed": self.speed, "support": self.motor2_support, "message": self.message,
                    "simulated": self.simulate, "battery": self.battery,
                    "toyConnected": self.toy_connected, "deviceName": self.device_name,
                    "lastDeviceCheckSec": freshness, "lastDeviceError": self.last_device_error,
                    "sessionCommands": self.session_commands,
                    "totalCommands": self.total_commands,
                    "faultLatched": self.fault_latched, "faultReason": self.fault_reason,
                    "stopPending": self.stop_pending, "stopAcks": self.stop_acks,
                    "stopAttempts": self.stop_attempts, "lastStopError": self.last_stop_error}

    def _pattern(self, mode, elapsed, maximum, speed, m1, m2, rnd, support=65):
        """Motor 1-led waveforms with independent, complementary Motor 2 accents.

        Timing is intentionally measured in seconds, not sub-second clicks.
        Motor 2 strength is user adjustable for preset modes; test, manual,
        and solo-motor modes remain unmodified.
        """
        factor = (speed + 1) / 4.0   # 0.5x at slowest, 1x default, 1.5x fastest
        t = max(0., elapsed * factor)
        if mode == "random":
            index = int(t / 18.)
            mode = rnd[index % len(rnd)] if rnd else "wave"
            t %= 18.
        if mode == "test":
            if elapsed < 2.2:
                return 4, 0
            if elapsed < 4.4:
                return 0, 4
            return 4, 4
        if mode == "manual":
            return min(maximum, m1), min(maximum, m2)
        if mode == "motor1":
            return maximum, 0
        if mode == "motor2":
            return 0, maximum

        # Smooth periodic swell: starts at a low point and rises to a peak.
        def swell(time_value, period):
            return (1.0 - math.cos(2.0 * math.pi * time_value / period)) / 2.0

        def triangle(time_value, period):
            position = (time_value % period) / period
            return 1.0 - abs(2.0 * position - 1.0)

        def pair(a, b):
            a = max(0., min(1., a))
            b = max(0., min(1., b))
            contribution = max(0., min(1., support / 100.))
            return round(maximum * a), round(maximum * b * contribution)

        if mode == "wave":
            # Motor 1 rises first; Motor 2 follows 2.6 phase-seconds later.
            return pair(.18 + .82 * swell(t, 10.), .88 * swell(t - 2.6, 10.))
        if mode == "sync":
            # Simultaneous timing with an adjustable Motor 2 level.
            w = swell(t, 9.)
            return pair(.18 + .82 * w, .18 + .82 * w)
        if mode == "pulse":
            # Overlapping bursts, with intentionally sustained phases.
            p = t % 8.5
            return pair(.87 if p < 4.0 else .08, .82 if 2.1 <= p < 5.5 else 0)
        if mode == "alternate":
            # Motor 1 leads for most of the cycle, then Motor 2 replies.
            p = t % 14.
            return pair(.91 if p < 7.3 else (.12 if p < 9.4 else 0),
                        .86 if 7.3 <= p < 12.3 else 0)
        if mode == "chase":
            # Motor 1 -> both -> Motor 2 -> rest.
            p = t % 15.
            if p < 4.4:
                return pair(.85, 0)
            if p < 9.0:
                return pair(.87, .85)
            if p < 12.6:
                return pair(0, .82)
            return pair(0, 0)
        if mode == "ramp":
            # Gradual rise/fall with an offset secondary rise.
            return pair(.12 + .88 * triangle(t, 14.),
                        .88 * triangle(t - 2.7, 14.))
        if mode == "anchor":
            # Continuous primary output; spaced accents from Motor 2.
            p = t % 10.
            return pair(.60 + .23 * swell(t, 10.), .95 if 4.0 <= p < 7.5 else .05)
        if mode == "heartbeat":
            # Distinct primary double pulse and delayed secondary beat.
            p = t % 17.2
            a = .87 if (1.0 <= p < 4.6 or 6.2 <= p < 9.8) else .09
            b = .95 if 10.1 <= p < 14.0 else 0
            return pair(a, b)
        if mode == "orbit":
            # Independent wave periods prevent repetitive perfect overlap.
            return pair(.30 + .70 * swell(t, 10.5),
                        .13 + .87 * swell(t + 2.7, 14.))
        if mode == "cascade":
            # Secondary wave follows primary by about three seconds.
            return pair(.20 + .80 * swell(t, 12.), .93 * swell(t - 3.0, 12.))
        if mode == "flutter":
            # Slow primary bed with clearly spaced secondary accents.
            p = t % 7.5
            return pair(.51 + .29 * swell(t, 12.), .92 if 2.0 <= p < 5.6 else 0)
        if mode == "tide":
            # Deep slow crescendos that crest at different times.
            return pair(.15 + .85 * swell(t, 16.), .90 * swell(t - 4., 16.))
        if mode == "echo":
            # Two distinct short responses rather than a symmetric overlap.
            p = t % 12.
            return pair(.84 if 0.8 <= p < 4.8 else (.34 if 5.0 <= p < 7.4 else .08),
                        .88 if 5.0 <= p < 9.4 else 0)
        if mode == "drift":
            # Slow, slightly asynchronous waves; avoids hard edges.
            return pair(.27 + .56 * swell(t, 18.), .18 + .74 * swell(t+3.9, 23.))
        if mode == "steps":
            # Smooth stepped plateaus, secondary climbing out of phase.
            p = t % 16.
            a = .26 if p < 4 else .48 if p < 8 else .77 if p < 12 else .35
            b = .12 if p < 4 else .33 if p < 8 else .55 if p < 12 else .87
            return pair(a, b)
        if mode == "ripple":
            # Nested slow waves with a drifting offset on the second motor.
            a = .24 + .53 * swell(t, 10.5) + .18 * swell(t, 3.7)
            b = .12 + .58 * swell(t+2.5, 12.7) + .22 * swell(t, 5.1)
            return pair(a, b)
        return 0, 0

    def _loop(self):
        while not self.close.is_set():
            with self.state_lock:
                mode = self.mode
                gen = self.generation
                end = self.end
                start = self.started
                cap = self.max_level
                speed = self.speed
                m1, m2 = self.motor1, self.motor2
                support = self.motor2_support
                rnd = self.random_modes
                director = self.director
                session_seconds = self.minutes * 60
            if mode == "idle":
                self.wake.wait(1)
                self.wake.clear()
                continue
            now = time.monotonic()
            if now >= end:
                # Only end the generation that actually expired.
                with self.state_lock:
                    still_current = gen == self.generation
                if still_current:
                    try:
                        self.stop("Session ended — automatic stop sent")
                    except RuntimeError:
                        pass
                continue
            if mode == "autonomous" and director is not None:
                a, b = director.levels(now - start, cap, speed, support, session_seconds)
            else:
                a, b = self._pattern(mode, now - start, cap, speed, m1, m2, rnd, support)
            try:
                self._send_levels(gen, a, b)
            except RuntimeError as exc:
                with self.state_lock:
                    still_current = gen == self.generation
                if still_current:
                    try:
                        self.stop(f"Connection error: {exc}", fault=True)
                    except RuntimeError:
                        pass
            # 0.9 s at speed 1, 0.4 s at speed 5 (LAN only).
            interval = 1.025 - .125 * speed
            self.wake.wait(min(interval, max(.08, end - time.monotonic())))
            self.wake.clear()

    def shutdown(self):
        self.close.set()
        self.wake.set()
        self.recovery_wake.set()
        try:
            self.stop("Dashboard shutting down")
        except RuntimeError:
            pass
        self.worker.join(timeout=3)
        self.telemetry_worker.join(timeout=3)
        self.recovery_worker.join(timeout=3)





HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0a101b"><title>PulseDirector · LAN Studio</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',Arial,sans-serif;color:#edf0fc;background:#0a101b;color-scheme:dark;--bg:#0a101b;--panel:#141d2b;--border:#2b3950;--dim:#93a1bc;--accent:#bba8ff;--teal:#80e9cd;--rose:#ff849a}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 50% -13%,#42376191 0,transparent 49%),radial-gradient(ellipse at 99% 14%,#0f555339 0,transparent 34%),#0a101b}
button,input,select{font:inherit}button{cursor:pointer;touch-action:manipulation}
button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #a6f4e1;outline-offset:3px}
.wrap{max-width:1080px;margin:0 auto;padding:30px 20px 110px}
.top{display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:28px}
.mark{display:flex;align-items:center;gap:12px}
.logo{width:49px;height:49px;display:grid;place-items:center;background:linear-gradient(140deg,#a897ff,#82e6d0);color:#101323;border-radius:16px;font-size:27px;font-weight:900;box-shadow:0 8px 30px #bba8ff3b}
.overline,.eyebrow,.live-label{color:#9ea9c1;font-size:10px;font-weight:850;letter-spacing:2px;text-transform:uppercase}
.title{font-size:25px;font-weight:860;letter-spacing:-1px;line-height:1.15}.brand-accent{color:#c4b6ff}.version{font-size:10px;letter-spacing:0;vertical-align:super;color:#b9c3db;margin-left:8px;font-weight:600}
.tiny,.muted{font-size:12px;color:#9eacc5;line-height:1.45}
.chip{display:flex;align-items:center;gap:9px;border:1px solid #40516d;background:#182235;border-radius:30px;padding:10px 14px;white-space:nowrap;font-weight:700;font-size:12px}
.dot{display:inline-block;width:9px;height:9px;background:#7e90ad;border-radius:50%}.dot.live{background:var(--teal);box-shadow:0 0 14px #80e9cd99}
.panel{background:linear-gradient(155deg,#192437,#121b2a);border:1px solid var(--border);border-radius:22px;padding:24px;margin:0 0 17px;box-shadow:0 14px 40px #060a1440}
.panel:first-of-type{background:linear-gradient(120deg,#352c50,#182438 54%,#152f35);border-color:#5b527b}
.eyebrow{margin:0 0 15px;color:#bbaff7}.status-overline{color:#8b96b0}
.status-box{display:flex;align-items:center;justify-content:space-between;gap:25px}
.status-name{font-size:clamp(23px,3.7vw,37px);font-weight:850;letter-spacing:-1.25px;line-height:1.12;margin:0 0 9px}
.status-message{max-width:610px;color:#c3cadd;font-size:13px;overflow-wrap:anywhere;line-height:1.5}
.timebox{text-align:right;min-width:100px}.countdown{font-variant-numeric:tabular-nums;font-size:31px;font-weight:850;letter-spacing:-1px}
.progress-track,.energy-track{height:6px;width:100%;background:#ffffff17;border-radius:22px;overflow:hidden;margin-top:21px}.progress-fill{height:100%;width:0%;background:linear-gradient(90deg,#9e8bff,#82e6d0);transition:width .3s}.scene-strip{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0 4px}.scene-chip{border:1px solid #7363986b;background:#8172b12a;padding:7px 10px;border-radius:20px;font-weight:750;font-size:11px;color:#ddd1ff}.scene-chip.subtle{color:#b4d9d3;background:#479f8c14;border-color:#479f8c52}
.stop{width:100%;margin-top:16px;border:1px solid #ffafbd;background:linear-gradient(105deg,#fa788f,#ffb1a7);color:#281322;font-size:16px;font-weight:900;letter-spacing:.4px;border-radius:13px;padding:16px;box-shadow:0 8px 21px #fb718542}.stop:hover{filter:brightness(1.07)}
.fault-banner{border:2px solid #ff657f;background:#3a1725;color:#ffe1e5;border-radius:15px;padding:16px;margin:0 0 17px;font-weight:700;line-height:1.5}
.fault-banner p{margin:7px 0;font-size:13px}.fault-banner button{margin-top:8px;background:#ffd2d9;border:0;color:#341a25;border-radius:10px;padding:12px;font-weight:850}
.fault-banner button:disabled{opacity:.45;cursor:not-allowed}
.sectionhead{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:0 0 18px}.sectionhead h2,h2{font-size:18px;font-weight:800;margin:0;letter-spacing:-.4px}.sub{color:#98a8c2;font-size:12px}
.stats-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px}
.stat{background:#0e1725a8;border:1px solid #293a50;border-radius:14px;padding:15px;min-width:0}.stat-label{font-size:11px;color:#98a8c3;margin-bottom:10px}.stat-number{font-variant-numeric:tabular-nums;font-size:26px;font-weight:850;overflow-wrap:anywhere}.stat-number.small-number{font-size:17px}.online{color:#82e9cb}.danger{color:#ff9bb0}
.battery-meter,.meter{height:7px;background:#344257;border-radius:22px;overflow:hidden;margin:10px 0 7px}.battery-fill{height:100%;width:0;background:linear-gradient(90deg,#63c2a8,#b2eed1);transition:width .4s}
.stats-bottom{margin-top:15px;display:flex;gap:12px 25px;flex-wrap:wrap;color:#aebbd0;font-size:12px}.stats-bottom b{color:#d4ddf2;font-variant-numeric:tabular-nums}
.modes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.mode{background:linear-gradient(145deg,#1c2a3c,#152030);border:1px solid #34445c;color:#e7e9fa;border-radius:14px;min-height:102px;text-align:left;padding:14px;display:flex;flex-direction:column;gap:7px;transition:background .13s,border-color .13s,transform .13s}.mode:hover{background:#2b3850;transform:translateY(-1px)}.mode.selected{background:linear-gradient(145deg,#413b67,#223447);border-color:#c1a7ff;box-shadow:inset 0 0 0 1px #b99bff44}.mode.featured-mode{grid-column:span 2;flex-direction:row;flex-wrap:wrap;align-content:center;align-items:center;gap:7px 14px;background:linear-gradient(120deg,#373053,#203b45)}.mode.featured-mode .desc{flex-basis:100%}.mode .sym{font-size:24px;color:#c7b8ff;line-height:1}.mode .txt{font-size:14px;font-weight:780}.mode .desc{font-size:11px;color:#abbad2;line-height:1.4}
.director-feature{background:linear-gradient(150deg,#302e50,#1c2b3b 66%,#182936);border-color:#7667a7}.director-feature h2{font-size:22px}.spark{color:#bdaaff}.director-feature .sub{line-height:1.6;margin-top:9px;max-width:750px}.director-options{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-top:20px}.director-options>div{min-width:0}.director-feature select{width:100%;background:#101d2e;border:1px solid #655f85;border-radius:11px;color:#f0edff;margin:7px 0 0;padding:12px;font-size:13px}.range-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:10px;font-size:13px}.range-wrap{margin-bottom:24px}.range-wrap:last-child{margin-bottom:0}.value{font-size:12px;font-weight:800;background:#3c365a;color:#ddd0ff;border-radius:8px;padding:6px 9px;font-variant-numeric:tabular-nums}input[type=range]{width:100%;height:26px;accent-color:#b9a3ff;cursor:pointer}
.director-live{margin-top:18px;border:1px solid #6f7da261;background:#101b2cb3;border-radius:15px;padding:18px}.director-live-head{display:flex;justify-content:space-between;align-items:center;gap:10px}.intent-line{margin-top:10px;font-weight:720;font-size:13px;color:#9dedda;letter-spacing:.1px}.scene-value{color:#c9befc;font-size:19px;font-weight:800;text-align:right}.director-live-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-top:17px}.director-live-grid>div{display:flex;flex-direction:column;gap:6px}.director-live-grid strong{font-size:16px;color:#e4e8f7}.energy-head{display:flex;justify-content:space-between;margin-top:16px;font-size:11px;font-weight:750;color:#b4bed6}.energy-track{margin-top:8px;height:6px}.energy-fill{background:linear-gradient(90deg,#61bda9,#b5a3ff,#ef9ab7);width:0;height:100%;transition:width .3s}
.director-idea{margin-top:13px;border:1px solid #635f8c;background:#38335158;border-radius:12px;padding:12px 14px;color:#c5c3e1;font-size:12px;line-height:1.5}
.rows{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:25px}.start{display:block;width:100%;border:0;border-radius:13px;background:linear-gradient(110deg,#bba8ff,#80dfce);color:#121b29;font-size:16px;font-weight:900;padding:16px;margin-top:15px;box-shadow:0 9px 22px #a0a1e32c}.start:hover{filter:brightness(1.08)}.secondary{background:#233147;color:#e8ebfa;border:1px solid #44516c;border-radius:11px;padding:11px 14px;font-size:13px;font-weight:700}.secondary:hover{background:#344460}.tools{display:flex;flex-wrap:wrap;gap:9px;margin-top:17px}.motor-name{display:flex;justify-content:space-between;gap:8px;align-items:center}.motor-name b{font-size:14px}.motor-read{color:#d0bbff;font-size:13px;font-weight:800}.meter{height:9px}.fill{height:100%;width:0%;background:linear-gradient(90deg,#9887f9,#83e6d4);transition:width .3s}.muted{margin:9px 0 0}.footer{text-align:center;font-size:11px;line-height:1.7;color:#7d8ea8;margin:23px auto;max-width:680px}
.modal{position:fixed;inset:0;z-index:30;background:#080e19ed;display:grid;place-items:center;padding:20px}.login{background:#182338;border:1px solid #4c5576;border-radius:20px;padding:28px;width:100%;max-width:400px}.login h2{font-size:23px}.login input{width:100%;margin:10px 0;padding:13px;background:#0d1625;border:1px solid #586b88;border-radius:11px;color:#fff;font-size:16px}.hide{display:none!important}.error{color:#ffadbb;font-size:12px;min-height:17px}
.stop-dock{position:fixed;bottom:calc(env(safe-area-inset-bottom, 0px) + 11px);right:16px;left:16px;z-index:16;display:none;align-items:center;gap:12px;max-width:460px;margin:auto;background:#152135f2;border:1px solid #a4667b;border-radius:16px;padding:9px 10px 9px 16px;box-shadow:0 9px 35px #050915a0;backdrop-filter:blur(12px);font-size:12px;color:#d6deef}.stop-dock button{margin-left:auto;background:#fc8194;border:0;border-radius:10px;color:#29121f;padding:10px 19px;font-size:13px;font-weight:900}
@media(max-width:760px){.modes{grid-template-columns:repeat(3,minmax(0,1fr))}.director-options{grid-template-columns:repeat(2,minmax(0,1fr))}.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stop-dock:not(.hide){display:flex}}
@media(max-width:530px){.wrap{padding:17px 12px 110px}.top{margin-bottom:19px}.logo{width:43px;height:43px;border-radius:14px}.title{font-size:21px}.chip{padding:8px 10px;font-size:11px}.panel{padding:17px;border-radius:17px}.status-box{align-items:flex-start}.status-name{font-size:24px}.countdown{font-size:23px}.timebox{min-width:75px}.modes{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.mode{min-height:98px;padding:11px}.mode.featured-mode{grid-column:span 2}.rows,.director-options{grid-template-columns:1fr;gap:11px}.director-live-grid{gap:8px}.director-live-grid strong{font-size:13px}.scene-value{font-size:16px}.sub{font-size:11px}.stats-grid{gap:8px}.stat{padding:12px}.stat-number{font-size:23px}.stat-number.small-number{font-size:15px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important}}

</style></head><body>
<div class="wrap">
<div class="fault-banner hide" id="faultBanner" role="alert" aria-live="assertive">
  ⚠ CONNECTION FAULT — PHYSICAL MOTOR STATE UNKNOWN
  <p id="faultDetail">Stop could not be confirmed. Physically turn off your Edge 2.</p>
  <p id="faultRecovery">Trying to send Stop when connection returns.</p>
  <button id="ackFault" type="button" disabled>Acknowledge after checking physical device</button>
</div>
<div class="top"><div class="mark"><div class="logo">✦</div><div><div class="overline">PRIVATE DEVICE STUDIO</div><div class="title">Pulse<span class="brand-accent">Director</span><span class="version">v4.5</span></div></div></div><div class="chip"><i class="dot" id="dot"></i><span id="pill">Standby</span></div></div>
<section class="panel"><div class="eyebrow">ON AIR <span class="status-overline">/ YOUR SESSION</span></div><div class="status-box"><div><div class="status-name" id="current">Ready to start</div><div class="status-message" id="msg">Connect Lovense Remote on home Wi-Fi and enable Game Mode.</div></div><div class="timebox"><div class="countdown" id="left">00:00</div><div class="tiny">remaining</div></div></div>
<div class="progress-track" aria-label="Session progress"><div id="sessionProgress" class="progress-fill"></div></div>
<div class="scene-strip"><span class="scene-chip" id="stageChip">Waiting for session</span><span class="scene-chip subtle" id="sceneChip">Live scene: —</span></div>
<button class="stop" id="stop">■ &nbsp; STOP ALL MOTORS</button></section>
<section class="panel stats-panel"><div class="sectionhead"><h2>Live telemetry</h2><span class="sub" id="updated">Checking device…</span></div>
<div class="stats-grid">
<div class="stat"><div class="stat-label">Edge 2 battery</div><div class="stat-number" id="battery">—</div><div class="battery-meter"><div class="battery-fill" id="batteryBar"></div></div><div class="tiny" id="batteryNote">Awaiting device report</div></div>
<div class="stat"><div class="stat-label">Device connection</div><div class="stat-number small-number" id="connection">Checking</div><div class="tiny" id="connectionNote">LAN Game Mode status</div></div>
<div class="stat"><div class="stat-label">Session elapsed</div><div class="stat-number" id="elapsed">00:00</div><div class="tiny">This session</div></div>
<div class="stat"><div class="stat-label">Commands sent</div><div class="stat-number" id="commands">0</div><div class="tiny" id="commandsNote">Does not prove physical vibration</div></div>
</div>
<div class="stats-bottom"><span>Motor 1 · prostate-facing: <b id="level1">0 / 20</b></span><span>Motor 2 · perineum: <b id="level2">0 / 20</b></span></div>
</section>
<section class="panel"><div class="sectionhead"><h2>Pattern library</h2><span class="sub">20 ways to play</span></div><div class="modes" id="modes">
<button class="mode selected featured-mode" data-mode="autonomous"><span class="sym">✦</span><span class="txt">Autonomous Director</span><span class="desc">Makes fresh decisions; no repeating pattern list</span></button>
<button class="mode" data-mode="wave"><span class="sym">∿</span><span class="txt">Wave</span><span class="desc">Motor 1 leads; Motor 2 follows</span></button>
<button class="mode" data-mode="pulse"><span class="sym">◉</span><span class="txt">Pulse</span><span class="desc">Overlapping primary-led bursts</span></button>
<button class="mode" data-mode="alternate"><span class="sym">⇄</span><span class="txt">Alternate</span><span class="desc">Longer Motor 1, then Motor 2</span></button>
<button class="mode" data-mode="chase"><span class="sym">↝</span><span class="txt">Chase</span><span class="desc">Primary, both, secondary, rest</span></button>
<button class="mode" data-mode="sync"><span class="sym">≈</span><span class="txt">Sync</span><span class="desc">Both rise and fall together</span></button>
<button class="mode" data-mode="ramp"><span class="sym">⌁</span><span class="txt">Ramp</span><span class="desc">Smooth rise with delayed accent</span></button>
<button class="mode" data-mode="anchor"><span class="sym">◈</span><span class="txt">Anchor</span><span class="desc">Steady Motor 1 with Motor 2 accents</span></button>
<button class="mode" data-mode="heartbeat"><span class="sym">♥</span><span class="txt">Heartbeat</span><span class="desc">Two Motor 1 pulses, Motor 2 replies</span></button>
<button class="mode" data-mode="orbit"><span class="sym">◎</span><span class="txt">Orbit</span><span class="desc">Different waves; Motor 1 leads</span></button>
<button class="mode" data-mode="cascade"><span class="sym">↠</span><span class="txt">Cascade</span><span class="desc">Motor 1 wave followed by Motor 2</span></button>
<button class="mode" data-mode="flutter"><span class="sym">❋</span><span class="txt">Flutter</span><span class="desc">Steady Motor 1 with spaced accents</span></button>
<button class="mode" data-mode="tide"><span class="sym">≋</span><span class="txt">Tide</span><span class="desc">Long offset swells across both</span></button>
<button class="mode" data-mode="echo"><span class="sym">↳</span><span class="txt">Echo</span><span class="desc">Motor 2 answers after Motor 1</span></button>
<button class="mode" data-mode="drift"><span class="sym">◌</span><span class="txt">Drift</span><span class="desc">Long, offset waves</span></button>
<button class="mode" data-mode="steps"><span class="sym">▥</span><span class="txt">Steps</span><span class="desc">Alternating intensity plateaus</span></button>
<button class="mode" data-mode="ripple"><span class="sym">≋</span><span class="txt">Ripple</span><span class="desc">Layered complementary waves</span></button>
<button class="mode" data-mode="random"><span class="sym">✳</span><span class="txt">Random Mix</span><span class="desc">Shuffles 16 patterns every ~18 sec</span></button>
<button class="mode" data-mode="motor1"><span class="sym">①</span><span class="txt">Motor 1</span><span class="desc">Run only the first motor</span></button>
<button class="mode" data-mode="motor2"><span class="sym">②</span><span class="txt">Motor 2</span><span class="desc">Run only the second motor</span></button>
</div></section>
<section class="panel director-feature" id="directorPanel"><div class="eyebrow">INTELLIGENT SEQUENCING · 100% LOCAL</div><h2>Autonomous Director <span class="spark">✦</span></h2><p class="sub">Makes deliberate moves, sometimes returns to an earlier theme, and varies holds and short resets. No person, sensory feedback or remote AI is involved.</p>
<div class="director-options">
<div><label for="directorStyle" class="tiny">Behaviour</label><select id="directorStyle"><option value="confident" selected>Confident · deliberate, stronger moves</option><option value="unpredictable">Unpredictable · balanced variety</option><option value="patient">Patient · longer phases</option><option value="playful">Playful · more back-and-forth</option><option value="progressive">Progressive · gradual build</option></select></div>
<div><label for="directorFlow" class="tiny">Session flow</label><select id="directorFlow"><option value="driving" selected>High energy · stronger, longer phases</option><option value="balanced">Balanced · steady variety</option><option value="build">Build · gradual climb</option><option value="waves">Waves · rolling energy arcs</option></select></div>
<div><div class="range-head"><label for="surprise">Surprise level</label><span class="value" id="surpriseVal">4 / 5</span></div><input id="surprise" type="range" min="1" max="5" step="1" value="4"></div>
</div><div class="director-live" aria-live="off">
<div class="director-live-head"><span class="live-label">DIRECTOR LIVE</span><span class="scene-value" id="sceneName">Waiting to start</span></div>
<div class="intent-line" id="intentLine" aria-live="polite">Choosing the next move</div>
<div class="director-live-grid"><div><span class="tiny">Session chapter</span><strong id="directorPhase">—</strong></div><div><span class="tiny">Scene countdown</span><strong id="sceneTime">—</strong></div><div><span class="tiny">New decisions</span><strong id="decisionCount">0</strong></div></div>
<div class="energy-head"><span>Energy profile</span><span id="energyVal">—</span></div><div class="energy-track"><div class="energy-fill" id="energyBar"></div></div>
</div><div class="director-idea" id="directorInfo">Director chooses each new move during the session. Maximum intensity, duration and Motor 2 contribution always remain bounded by your settings.</div></section>
<section class="panel"><div class="sectionhead"><h2>Session settings</h2><span class="sub">Adjust then press Start</span></div>
<div class="rows"><div><div class="range-wrap"><div class="range-head"><label for="max">Maximum intensity</label><span class="value" id="maxVal">10 / 20</span></div><input id="max" type="range" min="1" max="20" value="10"></div><div class="range-wrap"><div class="range-head"><label for="speed">Pattern speed</label><span class="value" id="speedVal">3 / 5</span></div><input id="speed" type="range" min="1" max="5" value="3"></div></div>
<div><div class="range-wrap"><div class="range-head"><label for="support">Motor 2 contribution</label><span class="value" id="supportVal">65%</span></div><input id="support" type="range" min="0" max="100" step="5" value="65"><p class="muted">Applies to the patterns above. Motor 1 leads; Motor 2 adds perineum-side accents. 100% keeps full programmed Motor 2 strength. Manual controls are unchanged.</p></div><div class="range-wrap"><div class="range-head"><label for="minutes">Session timer</label><span class="value" id="minutesVal">5 min</span></div><input id="minutes" type="range" min="0.5" max="20" step="0.5" value="5"></div><p class="muted">Every mode automatically stops when the timer ends. You can stop it at any time.</p></div></div>
<button class="start" id="start">▶ &nbsp; START AUTONOMOUS DIRECTOR</button>
</section>
<section class="panel"><div class="sectionhead"><h2>Individual motors</h2><span class="sub">Sliders enter Manual mode</span></div><div class="rows"><div class="range-wrap"><div class="motor-name"><b>Motor 1 · prostate-facing</b><span class="motor-read" id="m1Val">4 / 20</span></div><input id="m1" type="range" min="0" max="20" value="4"><div class="meter"><div class="fill" id="bar1"></div></div></div><div class="range-wrap"><div class="motor-name"><b>Motor 2 · perineum</b><span class="motor-read" id="m2Val">4 / 20</span></div><input id="m2" type="range" min="0" max="20" value="4"><div class="meter"><div class="fill" id="bar2"></div></div></div></div><p class="muted">Moving either slider while a session is running switches to manual control and restarts the selected timer. Levels remain capped by Maximum intensity.</p><div class="tools"><button class="secondary" id="manual">▶ Run manual levels</button><button class="secondary" id="test">Test both motors (7 sec)</button><button class="secondary" id="check">Check connection</button></div></section>
<p class="footer">PulseDirector v4.5 · LAN Edition · Edge 2 only.<br>Run only on a trusted local network or private VPN. Never forward this dashboard to the public internet.</p>
</div>
<div class="stop-dock hide" id="stopDock"><span>Session running</span><button type="button" id="dockStop" aria-label="Stop all motors immediately">■ STOP ALL</button></div>
<div class="modal" id="login"><form class="login" id="loginForm"><div class="overline">LOCAL DEVICE CONTROL</div><h2 style="margin:12px 0 7px">Unlock dashboard</h2><p class="muted">Enter the access key shown in the Raspberry Pi terminal on first launch. It is also saved in <code>.edge_dashboard_key</code> beside the application.</p><label class="tiny" for="key">Access key</label><input id="key" type="password" autocomplete="off" required placeholder="Paste your access key"><button class="start" type="submit">Unlock controls</button><div class="error" id="loginError"></div></form></div>
<script>
(()=>{'use strict';
const $=id=>document.getElementById(id);
let key=sessionStorage.getItem('edgeKey')||'',mode='autonomous',lastRunning=false,sliderTimer=null,pending=false;
const modes=[...document.querySelectorAll('.mode')];
const labels={idle:'Ready to start',autonomous:'Autonomous Director',wave:'Wave',pulse:'Pulse',alternate:'Alternate',chase:'Chase',sync:'Sync',ramp:'Ramp',anchor:'Anchor',heartbeat:'Heartbeat',orbit:'Orbit',cascade:'Cascade',flutter:'Flutter',tide:'Tide',echo:'Echo',drift:'Drift',steps:'Steps',ripple:'Ripple',random:'Random Mix',motor1:'Motor 1',motor2:'Motor 2',manual:'Manual Control',test:'Motor Test'};
function select(name){mode=name;modes.forEach(b=>b.classList.toggle('selected',b.dataset.mode===name));$('directorPanel').classList.toggle('hide',name!=='autonomous');$('start').textContent=name==='autonomous'?'▶  START AUTONOMOUS DIRECTOR':'▶  START SELECTED PATTERN'}
modes.forEach(b=>b.addEventListener('click',()=>select(b.dataset.mode)));
function settings(m=''){return {mode:m||mode,max:Number($('max').value),speed:Number($('speed').value),support:Number($('support').value),minutes:Number($('minutes').value),motor1:Number($('m1').value),motor2:Number($('m2').value),style:$('directorStyle').value,flow:$('directorFlow').value,surprise:Number($('surprise').value)}}
function refreshValues(){for(const [id,suffix] of [['max',' / 20'],['speed',' / 5'],['support','%'],['minutes',' min'],['m1',' / 20'],['m2',' / 20'],['surprise',' / 5']]) $(id+'Val').textContent=$(id).value+suffix}
['max','speed','support','minutes','m1','m2','surprise'].forEach(id=>$(id).addEventListener('input',refreshValues));refreshValues();
async function api(path,data){const opts={headers:{'X-Edge-Key':key}};if(data!==undefined){opts.method='POST';opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(data)}const response=await fetch(path,opts);let result={};try{result=await response.json()}catch(e){}if(response.status===401){sessionStorage.removeItem('edgeKey');$('login').classList.remove('hide');throw Error('Invalid access key')}if(!response.ok||result.error)throw Error(result.error||'HTTP '+response.status);return result}
function duration(n){return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0')}
function display(s){
$('faultBanner').classList.toggle('hide',!s.faultLatched);
$('faultDetail').textContent=s.faultLatched?'Connection fault: '+(s.faultReason||s.message||'unknown')+'. Check the toy physically.':'';
$('faultRecovery').textContent=s.stopPending?'Automatic Stop pending; retrying after reconnection. '+(s.lastStopError||''):'Stop accepted by phone API; physical state is NOT verified. Check toy and acknowledge to unlock.';
$('ackFault').disabled=!s.faultLatched||!!s.stopPending;
$('start').disabled=!!s.faultLatched;$('manual').disabled=!!s.faultLatched;$('test').disabled=!!s.faultLatched;
lastRunning=!!s.running;$('current').textContent=labels[s.mode]||s.mode;$('msg').textContent=s.message||'Ready';$('pill').textContent=s.running?'Running':'Standby';$('dot').classList.toggle('live',s.running);$('stopDock').classList.toggle('hide',!s.running);let n=Math.max(0,s.secondsLeft||0);$('left').textContent=String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');$('sessionProgress').style.width=(s.sessionProgress||0)+'%';$('bar1').style.width=(s.motor1||0)*5+'%';$('bar2').style.width=(s.motor2||0)*5+'%';
$('level1').textContent=(s.motor1||0)+' / 20';$('level2').textContent=(s.motor2||0)+' / 20';
$('battery').textContent=s.battery==null?'—':s.battery+'%';$('batteryBar').style.width=s.battery==null?'0%':s.battery+'%';
$('batteryNote').textContent=s.battery==null?'No battery report':'Reported by Lovense Remote';
$('connection').textContent=s.toyConnected===true?'Connected (LAN)':'Not connected';
$('connection').className='stat-number small-number '+(s.toyConnected===true?'online':'danger');
$('connectionNote').textContent=s.toyConnected===true?'Edge 2 via Game Mode':s.lastDeviceError||'Check Lovense Remote Game Mode';
$('elapsed').textContent=duration(s.elapsedSeconds||0);$('commands').textContent=s.sessionCommands||0;
$('commandsNote').textContent='Commands sent; physical vibration not verified';
const director=s.mode==='autonomous'&&s.running;
$('sceneName').textContent=director?(s.directorScene||'Preparing'):'Waiting to start';
$('directorPhase').textContent=director?(s.directorPhase||'Preparing'):'—';
const nextIntent=director?(s.directorIntent||'Choosing the next move'):'Ready for your next session';if($('intentLine').textContent!==nextIntent)$('intentLine').textContent=nextIntent;
$('sceneTime').textContent=director?(s.directorSceneSecondsLeft||0)+'s':'—';
$('decisionCount').textContent=director?(s.directorDecisions||0):'0';
$('energyVal').textContent=director?(s.directorEnergy||0)+'%':'—';
$('energyBar').style.width=director?(s.directorEnergy||0)+'%':'0%';
$('stageChip').textContent=director?'CHAPTER · '+(s.directorPhase||'Preparing'):(s.running?'PATTERN · '+(labels[s.mode]||s.mode):'Waiting for session');
$('sceneChip').textContent=director?'SCENE · '+(s.directorScene||'Preparing'):(s.running?'Running · '+(labels[s.mode]||s.mode):'Live scene · —');
$('directorInfo').textContent=director?'Local scene planner · '+(s.directorDecisions||0)+' decisions · '+(s.directorReprises||0)+' deliberate callbacks · '+(s.directorFlow||'balanced')+' flow. No sensory feedback or live human operator.':'A local scene planner, not a person or responsive AI. Every change stays within your maximum intensity, timer and Motor 2 contribution.';
$('updated').textContent=s.lastDeviceCheckSec==null?'Checking device…':'LAN checked '+s.lastDeviceCheckSec+'s ago';}
function error(e){$('msg').textContent=e.message||String(e)}
async function run(path,body){if(pending)return;pending=true;try{display(await api(path,body))}catch(e){error(e)}finally{pending=false}}
$('start').onclick=()=>run('/api/start',settings());
// STOP must never be blocked by a pending Start or other UI request.
const stopNow=async()=>{try{display(await api('/api/stop',{}))}catch(e){error(e)}};
$('stop').onclick=stopNow; $('dockStop').onclick=stopNow;
$('manual').onclick=()=>run('/api/start',settings('manual'));
$('test').onclick=()=>run('/api/test',{});
$('ackFault').onclick=()=>run('/api/ack-fault',{});
$('check').onclick=async()=>{try{const x=await api('/api/check');display(x);$('msg').textContent=x.toyConnected?'Edge 2 reported connected via LAN':'Device not connected — verify Lovense Remote Game Mode' }catch(e){error(e)}};
['m1','m2'].forEach(id=>$(id).addEventListener('input',()=>{if(!lastRunning)return;clearTimeout(sliderTimer);sliderTimer=setTimeout(()=>run('/api/start',settings('manual')),330)}));
$('loginForm').addEventListener('submit',async e=>{e.preventDefault();key=$('key').value.trim();try{display(await api('/api/status'));sessionStorage.setItem('edgeKey',key);$('login').classList.add('hide');$('loginError').textContent=''}catch(e){$('loginError').textContent=e.message}});
async function poll(){if(!key||!$('login').classList.contains('hide'))return;try{display(await api('/api/status'))}catch(e){error(e)}}
setInterval(poll,1000);
if(key){api('/api/status').then(s=>{display(s);$('login').classList.add('hide')}).catch(()=>{sessionStorage.removeItem('edgeKey');$('login').classList.remove('hide')})}
})();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "EdgeLocal/1.0"
    def log_message(self, fmt, *args):
        # Avoid filling journals with 1-second polling requests.
        if args and str(args[0]).startswith('GET /api/status '):
            return
        print(f"[{self.log_date_time_string()}] {self.client_address[0]}: {fmt % args}", file=sys.stderr)

    def _reply(self, code, content, content_type):
        body = content.encode("utf-8") if isinstance(content, str) else content
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        self._reply(code, json.dumps(data), "application/json; charset=utf-8")

    def _authorized(self):
        return hmac.compare_digest(self.headers.get("X-Edge-Key", ""), self.server.key)

    def _needs_auth(self):
        if self._authorized():
            return False
        self._json(401, {"error": "Invalid access key"})
        return True

    def do_GET(self):
        if self.path == "/":
            self._reply(200, HTML, "text/html; charset=utf-8")
        elif self.path == "/favicon.ico":
            self._reply(200, b"", "image/x-icon")
        elif self.path in ("/api/status", "/api/check"):
            if self._needs_auth(): return
            if self.path == "/api/status":
                self._json(200, self.server.engine.status())
            else:
                try:
                    self._json(200, self.server.engine.refresh_toys())
                except RuntimeError as exc:
                    self._json(503, {"error": str(exc)})
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path not in ("/api/start", "/api/stop", "/api/test", "/api/ack-fault"):
            self._json(404, {"error": "Not found"}); return
        if self._needs_auth(): return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 2048: raise ValueError("Request too large")
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            if self.path == "/api/stop":
                result = self.server.engine.stop()
            elif self.path == "/api/ack-fault":
                result = self.server.engine.acknowledge_fault()
            elif self.path == "/api/test":
                result = self.server.engine.test()
            else:
                result = self.server.engine.start(data)
            self._json(200, result)
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except RuntimeError as exc:
            self._json(503, {"error": str(exc)})


def access_key():
    if KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if len(key) < 12:
            raise RuntimeError("Existing access key file seems invalid")
        KEY_FILE.chmod(0o600)
        return key
    key = secrets.token_urlsafe(18)
    fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    return key


def main():
    p = argparse.ArgumentParser(description="PulseDirector v4.5 LAN Edition — Edge 2 only")
    p.add_argument("--phone", help="IPv4 address shown in Lovense Remote Game Mode")
    p.add_argument("--port", type=int, default=8765, help="Dashboard port (default: 8765)")
    p.add_argument("--bind", default="127.0.0.1", help="Dashboard bind address (default: loopback; use your Pi LAN address for phone access)")
    p.add_argument("--no-print-key", action="store_true", help="Do not print the dashboard access key")
    p.add_argument("--simulate", action="store_true", help="Simulate device I/O; no physical motor commands")
    args = p.parse_args()
    if not args.simulate and not args.phone:
        p.error("--phone is required for live LAN control")
    if args.phone:
        try:
            addr = ipaddress.ip_address(args.phone)
            if not isinstance(addr, ipaddress.IPv4Address) or not addr.is_private or addr.is_loopback or addr.is_unspecified:
                p.error("--phone must be a private non-loopback IPv4 address on your LAN")
        except ValueError:
            p.error("--phone must be an IPv4 address shown in Game Mode")
    if args.port < 1 or args.port > 65535:
        p.error("--port must be in range 1..65535")
    key = access_key()
    engine = Engine(args.phone or "127.0.0.1", simulate=args.simulate)
    try:
        http = ThreadingHTTPServer((args.bind, args.port), Handler)
    except OSError:
        engine.shutdown()
        raise
    http.engine, http.key = engine, key
    print("\n  PulseDirector v4.5 — LAN Edition (Edge 2 only)\n")
    print(f"  Dashboard bind: {args.bind}:{http.server_port}")
    if not args.no_print_key:
        print(f"  Access key: {key}")
    else:
        print(f"  Access key file: {KEY_FILE} (never logged)")
    print(f"  Phone Game Mode IP: {args.phone or 'simulation'}")
    print(f"  Mode: {'SIMULATED' if args.simulate else 'LIVE LAN'}")
    print("  Keep the dashboard on a trusted LAN or private VPN. Do not port-forward it.\n", flush=True)

    def handle_signal(signum, frame):
        threading.Thread(target=http.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        http.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
        engine.shutdown()
        print("Dashboard stopped; STOP attempted if the phone was reachable.")


if __name__ == "__main__":
    main()
