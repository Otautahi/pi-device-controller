# Install PulseDirector v4.5 LAN Edition

**Experimental release-candidate instructions, not a stable release.** The updated LAN-only build passed 40 offline tests across Python 3.10–3.13 in GitHub Actions and limited off-body hardware checks on one Edge 2 (including Bluetooth/Wi-Fi interruption and automatic Stop recovery). The toy briefly vibrated on Bluetooth reconnection before automatically stopping. These results do not establish physical fail-safe performance. Public stable publication still requires final safety, fresh-install and owner approval. [API-terms ambiguity](https://github.com/Otautahi/pulse-director/issues/4) is documented as a clarification rather than a definitive prohibition. Keep any existing working controller installed separately.

## 1. Requirements

- Raspberry Pi OS or another Linux distribution, with **Python 3.10+** and Git
- Lovense Edge 2 with the Lovense Remote phone app
- Lovense Remote **Game Mode enabled**
- A trusted LAN on which the Pi can reach the phone's Game Mode IPv4 address
- An independent way to physically disconnect/stop the device

**Not technically required for this specific local transport:** cloud API token, QR pairing service, Cloud Keeper, pip dependencies, Pi-hole or WireGuard. Cloud mode and Max 2 are not supported. Vendor developer/API terms may still impose registration, permissions or conditions on distribution; see [issue #4](https://github.com/Otautahi/pulse-director/issues/4).

On Debian / Raspberry Pi OS, install Python and Git if needed:

```bash
sudo apt update
sudo apt install -y python3 git
python3 --version
```

Use a separate directory from any existing software.

## 2. Clone the release candidate

```bash
cd ~
git clone --branch release/v4.5.0-lan-rc1 --single-branch https://github.com/Otautahi/pulse-director.git pulse-director-lan
cd pulse-director-lan
python3 -m unittest discover -s tests -v
```

Tests simulate device replies and do **not** command physical motors. An automated pass is not proof of real-device compatibility.

## 3. Try the simulation first

Run locally on the Pi:

```bash
python3 edge_dashboard.py --simulate
```

The dashboard defaults to **127.0.0.1:8765** and prints a generated access key. On the Pi itself, open `http://127.0.0.1:8765` and enter that key.

If you use a headless Pi, the easiest way to view simulation from a PC is an SSH tunnel:

```bash
ssh -L 8765:127.0.0.1:8765 YOUR_PI_SSH_USER@YOUR_PI_LAN_IP
```

Run the simulation in the SSH session or another Pi terminal, then open `http://127.0.0.1:8765` on **your PC**. If that port is already used on your PC, change the *first* 8765 in the SSH command to another free local port.

Alternatively, on a trusted isolated LAN only, bind the simulator to the Pi LAN address with `--simulate --bind YOUR_PI_LAN_IP` and open `http://YOUR_PI_LAN_IP:8765`. Do not port-forward.

Press **Ctrl+C** to exit.

## 4. Connect the Edge 2 over LAN

1. Turn on the Edge 2 and pair it in **Lovense Remote**.
2. Disconnect Max 2 and all other Lovense toys: this build supports **one Edge 2 only**.
3. Enable **Game Mode** in Lovense Remote; note the **phone's Game Mode IPv4 address**.
4. Ensure the phone and Pi are on the same trusted, mutually reachable network. Guest isolation, VLAN firewall rules, or phone switching to cellular can prevent access.
5. Off-body and at the lowest intensity, start:

```bash
cd ~/pulse-director-lan
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP --bind YOUR_PI_LAN_IP
```

Use actual addresses shown on *your* network. `--phone` must be a private LAN IPv4 address. `--bind` is the Pi interface to serve the web dashboard on; its safe default is `127.0.0.1`.

Open `http://YOUR_PI_LAN_IP:8765` from a browser on your trusted LAN and enter the key printed on the Pi.

`--port 8765` is optional; supply another port if necessary. A local firewall must allow the selected port from your trusted client devices only.

## 5. Verify the real hardware off-body

Before use:

1. Confirm that the dashboard identifies a **single connected Edge 2**. If it refuses the model, **do not override the restriction**; file a sanitized compatibility report.
2. Try Motor 1 and Motor 2 separately at the lowest intensity.
3. Start a very short session and press **Stop all motors**.
4. Verify automatic timer expiry and mode switching.
5. During any testing of recovery from Wi-Fi/Bluetooth interruption, keep the toy **off-body** and the physical power button immediately accessible. Communication failure can prevent Stop commands from reaching the toy; on reconnection it may briefly activate before automatic retries stop it.

**Important:** The software can only attempt Stop over the same connection as Start. Its fault latch blocks further sessions until the phone API accepts recovery Stop commands and the operator physically checks the toy and acknowledges the warning. An API acknowledgement is not independent evidence that the motors stopped. A phone, Bluetooth, network or hardware failure can prevent an immediate remote Stop.

## 6. Access key and safe deployment

At first launch, PulseDirector generates a random access key in `.edge_dashboard_key` beside `edge_dashboard.py`, with owner-only file permissions. Keep it private. Never paste it into GitHub, logs, screenshots or issues. The app uses HTTP, **not TLS**, so treat anyone who can reach the page or intercept LAN traffic as a potential controller.

- Do **not** expose or forward port `8765` on your router.
- Use a trusted LAN or a properly configured private VPN; limit access to authorized devices.
- Don't install public code on the live Pi service before testing it.
- This release candidate deliberately does **not** install a systemd service or auto-start active sessions.

## 7. Updates and troubleshooting

To fetch later changes to the **same candidate branch**, stop the test server and run:

```bash
cd ~/pulse-director-lan
git pull --ff-only
python3 -m unittest discover -s tests -v
```

Do not automatically upgrade the private controller or overwrite its key/config. For connection errors, unavailable addresses, access-key problems and compatibility warnings, see [Troubleshooting](TROUBLESHOOTING.md) and [Security](SECURITY.md).
