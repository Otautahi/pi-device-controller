# Install PulseDirector v4.5 LAN Edition

These commands describe a **fresh, separate directory**. Never install over an already-working controller until the build has passed real-device validation.

## Prerequisites

- Linux / Raspberry Pi OS, Python 3.10+ recommended (standard library only)
- Lovense Edge 2; phone with Lovense Remote and Game Mode enabled
- Phone and Pi on the same trusted LAN (or reachable through a properly configured private route)
- Knowledge of your phone's **Game Mode IPv4 address** and your Pi's LAN IPv4 address

No developer-account token or cloud service is required.

## Installation

Unzip the reviewed source package into a **new directory**. From that folder:

```bash
python3 --version
python3 -m unittest discover -s tests -v
python3 edge_dashboard.py --simulate
```

The simulation listens only on `127.0.0.1` by default and sends no device commands. Stop with Ctrl+C.

Start live mode, substituting addresses shown on *your* network (example placeholders are not real addresses):

```bash
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP --bind YOUR_PI_LAN_IP
```

Open `http://YOUR_PI_LAN_IP:8765` from a browser connected to your trusted LAN; enter the generated access key shown on the Pi terminal. The key is saved as `.edge_dashboard_key` within the release directory; its permissions are restricted to the owner. Never commit, upload or screenshot it.

## Stop and recovery

- Press the **Stop all motors** control when needed.
- Physically disconnect/turn off the Edge 2 if Stop cannot reach the phone or Bluetooth is interrupted.
- Timed commands are short (`timeSec=2`) but immediate physical stop is **not guaranteed** during a connection failure.
- Do not configure auto-restart of an active session after connectivity loss.

## Check behaviour before first real use

1. Disconnect all devices other than Edge 2, especially Max 2.
2. Run simulation checks, then connect the Edge 2 through Game Mode.
3. Test off-body at minimum intensity; verify Motor 1 and Motor 2 separately.
4. Test Stop, automatic expiry and switching modes.
5. Disconnect phone Wi-Fi during an off-body session and confirm safe behaviour.

## Local access only

`--bind` defaults to `127.0.0.1` for safety. If accessing from your phone, bind specifically to the Pi's LAN address. **Do not** forward port 8765 on your router or expose the dashboard over the public internet. This application uses plain HTTP and a local access key, so only use a trusted LAN or a private, well-configured VPN.

No systemd service is supplied with this release candidate; first confirm device behaviour in an interactive session before considering one.
