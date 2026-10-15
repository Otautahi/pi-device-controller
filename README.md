# PulseDirector v4.5 — LAN Edition (release candidate)

A self-hosted, browser-based **Lovense Edge 2** controller for Linux / Raspberry Pi, using Lovense Remote's **local Game Mode** connection. No developer token, pairing QR, remote pairing service or online control backend is included.

> **Release candidate, not a supported hardware-tested release.** The LAN-only conversion has been tested offline against simulation and synthetic device replies; it has **not yet been verified on an actual Edge 2**. Do not expose the dashboard to the internet. Test off-body first and keep a physical way to stop or disconnect the device.

## Features

- Independent Motor 1 / Motor 2 commands, timed sessions, manual controls and a Stop button
- 20+ modes including Autonomous Director: Confident, Unpredictable, Patient, Playful, Progressive
- Director flows: High energy, Balanced, Build, Waves; Surprise levels 1–5
- Scene changes, deliberate holds, theme callbacks and live intent/energy display
- Preset caps for intensity, speed, duration and secondary motor contribution
- No additional Python dependencies; Python 3 standard library
- Optional `--simulate` mode for interface checks without sending commands

## Quick start

```bash
# In a new directory containing edge_dashboard.py and edge2_director.py:
python3 -m unittest discover -s tests -v
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP --bind YOUR_PI_LAN_IP
```

On your phone, enable **Lovense Remote → Game Mode**, find the phone's local IPv4 address, and keep that phone on the **same trusted network** as the Pi. Open `http://YOUR_PI_LAN_IP:8765` from a browser on the same network. The access key is printed at first start and saved to `.edge_dashboard_key` alongside the application. Do not publish it.

For an offline simulator on the Pi only:

```bash
python3 edge_dashboard.py --simulate
# Dashboard: http://127.0.0.1:8765, from that machine
```

See [installation instructions](docs/INSTALL.md), [security notes](docs/SECURITY.md), and [release checklist](docs/RELEASE_CHECKLIST.md).

## Device restrictions

The LAN controller **accepts only a single connected device that Game Mode identifies by its model as `Edge` or `Edge 2`**. It refuses unknown models and concurrent devices. A user-defined nickname by itself does not count as device verification. This protection needs testing against real firmware responses before public release; different versions may report their names differently.

**Max 2 and other devices are not supported**. Disconnect them while testing. There is no multi-device feature in this edition.

## How it works

```text
Browser on trusted LAN / private VPN
         |
PulseDirector dashboard on Linux / Raspberry Pi
         |
Local Lovense Game Mode HTTP API (phone IPv4:20010)
         |
Phone running Lovense Remote → Bluetooth → Edge 2
```

The Director is a local rule-based scene planner; it does not sense reactions or represent a person controlling the device. Telemetry is reported by the phone app, not independently measured by PulseDirector. A successful API response does not prove a command physically reached a motor.

## Privacy

Do not commit `.edge_dashboard_key`, local logs, screenshots of active device IDs, IP-specific configs, or backups. The distribution intentionally uses **placeholders** in documentation and requires entering your own phone and Pi LAN addresses at runtime. A clean `.gitignore` helps, but inspect staged files and Git history before publishing.

## Licence and release status

The PulseDirector source is provided under the [MIT licence](LICENSE). The Lovense software, services, trademarks and protocols are not licensed by PulseDirector. Third-party API/distribution terms may affect publication or operation of software using the Lovense API; check current provider requirements before public redistribution. See [release checklist](docs/RELEASE_CHECKLIST.md).

This is an independent community project and is not affiliated with or endorsed by Lovense.
