# PulseDirector v4.5.0 LAN Edition — Experimental Prerelease

**Experimental prerelease — not a stable or safety-certified product.** This independent, non-commercial, open-source project is unaffiliated with Lovense.

## Overview
- Self-hosted browser controller for **one Lovense Edge 2**, using Lovense Remote's **local Game Mode** API through a phone and Raspberry Pi/Linux.
- 20+ modes, independently controlled motors and a rule-based Autonomous Director with adjustable energy, scene flow, surprise, intensity and session time.
- Access-key-protected web dashboard, local-only transport and offline simulation.
- **No** Lovense cloud API, Cloud Keeper, Max 2 support or simultaneous multi-device control.

## Connection recovery
- Stops an active software session on detected Bluetooth/Wi-Fi/Game Mode failure and attempts a Stop command.
- Retries multiple Stop commands after the Edge 2 reconnects.
- Displays a physical-state-unknown fault warning and blocks new sessions until recovery and explicit operator acknowledgement.
- Prioritizes Stop over concurrent Start/Test requests; 40 offline regression tests.

**Critical limitation:** With Bluetooth/Wi-Fi disconnected, software cannot send a physical Stop to the device. In a controlled off-body test, **Bluetooth reconnection triggered a brief vibration before automatic Stop succeeded**. An API success confirms a phone acknowledgement, **not** independently measured physical motor inactivity. Keep the device's physical power button accessible. See [issue #2](https://github.com/Otautahi/pulse-director/issues/2).

## Validation (owner-observed, 16–17 October 2026)
- One real Edge 2: detection, both motors, Stop, timed Director session and session expiry worked.
- On Bluetooth loss/reconnect: software fault latch appeared; after reconnect, a **brief vibration stopped automatically** without manual intervention; acknowledgement cleared the lock.
- On phone Wi-Fi loss/reconnect: motors stopped, stayed stopped, the recovery process completed and acknowledgement restored controls.
- **40 offline tests passed on Python 3.10, 3.11, 3.12 and 3.13** in GitHub Actions. The owner ran the preceding 39-test build, then the full 40-test build, on the Raspberry Pi.
- Not a fresh independent Raspberry Pi OS deployment certification or a guarantee across all firmware and network conditions.

## Get started
Download this tag's source archive or clone the pinned release tag:

```bash
git clone --branch v4.5.0-lan-rc.1 --single-branch https://github.com/Otautahi/pulse-director.git pulse-director-lan
cd pulse-director-lan
python3 -m unittest discover -s tests -v
python3 edge_dashboard.py --simulate
```

For the real Edge 2, follow [the installation guide](https://github.com/Otautahi/pulse-director/blob/v4.5.0-lan-rc.1/docs/INSTALL.md). Test **off-body first** at low intensity. Use a trusted local network; the dashboard uses HTTP with an access key. **Never port-forward the dashboard**.

## Terms and compatibility
MIT applies to the independent project source, not to Lovense software or marks. [Issue #4](https://github.com/Otautahi/pulse-director/issues/4) records an open question about third-party API distribution conditions; it does not assert the project is prohibited or endorsed. See the [release checklist](https://github.com/Otautahi/pulse-director/blob/v4.5.0-lan-rc.1/docs/RELEASE_CHECKLIST.md) and [security guidance](https://github.com/Otautahi/pulse-director/blob/v4.5.0-lan-rc.1/docs/SECURITY.md).
