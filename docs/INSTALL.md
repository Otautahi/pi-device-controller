# Installation guide — Edge 2 only

> **Pre-release documentation.** The public repository does not yet contain an officially released controller. Follow these steps **after** a tested release is published. They are for the **Lovense Edge 2 only**. Keep other Lovense devices disconnected.

This guide uses Raspberry Pi OS as the tested Linux example, a Windows PC for initial setup, and an Android phone running Lovense Remote. The controller is intended for other Linux hosts too, but those installations have not yet been verified. Linux/macOS users can adapt the SSH commands. You don't need prior GitHub experience.

## 1. What you need

- A Linux host with Python 3, an internet connection and SSH; the original development and tested platform is Raspberry Pi 3B+ running Raspberry Pi OS.
- Python 3, `curl`, `python3-venv` and sufficient permissions to install packages.
- A **Lovense Edge 2** and Lovense Remote on your phone, paired through Bluetooth.
- A trusted home network. For control **away from home**, a private VPN (for example WireGuard) that can reach the Pi's home LAN address.
- For optional cloud operation: **your own** Lovense Developer Token and registered platform name. [Lovense Developer](https://developer.lovense.com/).

Do not install over an existing working controller folder. Back up an existing installation and start with a new directory.

## 2. Get onto the Pi

From **Windows Command Prompt** (not inside the Pi SSH terminal):

```cmd
ssh YOUR_PI_USERNAME@YOUR_PI_IP
```

Replace `YOUR_PI_USERNAME` and `YOUR_PI_IP` with your own values. If SSH asks to trust a new host key, verify that you're connecting to your actual Pi before accepting it. SSH passwords don't display while typing.

After connecting, the prompt should show something like `user@raspberrypi:~ $`. Commands in the remaining `bash` blocks run **there, on the Pi**.

## 3. Download a tagged release

After the first release appears under **[GitHub Releases](https://github.com/Otautahi/pulse-director/releases)**, use the tagged source archive or clone the repository. For example:

```bash
cd ~
git clone https://github.com/Otautahi/pulse-director.git
cd pulse-director
```

If `git` is unavailable, run `sudo apt install -y git`. **Do not expect a runnable controller in the GitHub repository until the code is released.**

## 4. Install Python dependencies

```bash
sudo apt update
sudo apt install -y python3-venv curl libopenjp2-7
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The optional cloud keeper requires the virtual environment's Socket.IO and QR image packages. **Don't install these packages into Pi-hole's system environment.**

Run the offline, **no-device** test first:

```bash
python3 scripts/smoke_test.py
```

The smoke test does not intentionally send toy commands. Passing it doesn't prove real-device operation.

## 5. Test the dashboard in simulation

On the Pi:

```bash
python3 edge_dashboard.py --simulate --bind 127.0.0.1 --port 8765 --no-print-key
```

Leave this terminal open. In another SSH session, retrieve the dashboard key **privately**:

```bash
cd ~/pulse-director
cat .edge_dashboard_key
```

To open the simulation from Windows, use a **new Windows Command Prompt**:

```cmd
ssh -L 8765:127.0.0.1:8765 YOUR_PI_USERNAME@YOUR_PI_IP
```

Then open `http://127.0.0.1:8765` on that Windows PC. Stop simulation with `Ctrl+C` before running real hardware.

## 6. Local Edge 2 control at home

1. On your phone, connect **only your Edge 2** in Lovense Remote.
2. Enable **Game Mode → LAN** and find the phone's local Wi-Fi IP address.
3. Ensure the phone and Pi are on the same trusted LAN and phone Game Mode remains active.
4. Start the controller on the Pi, replacing the placeholders:

```bash
cd ~/pulse-director
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP --bind YOUR_PI_LAN_IP --port 8765 --no-print-key
```

Open `http://YOUR_PI_LAN_IP:8765` in a browser on the same LAN, enter the dashboard key and use a **short, low-intensity off-body test**. Verify the emergency Stop button and session end. Leave the command running during testing; `Ctrl+C` stops the server.

**Never configure `--bind 0.0.0.0` or open port `8765` to the internet.** The app requires a specific private interface and serves HTTP, not HTTPS.

## 7. Optional cloud control — developer registration and token

You can skip this entire section for LAN-only use.

1. Register **your own** Lovense developer platform and retain its exact platform name.
2. Choose a stable, unique **UID for your installation** (for example, a random identifier you create). Use the *same* UID in the dashboard and Cloud Keeper. Don't reuse someone else's UID.
3. Save the developer token **privately** on the Pi. Run the `read` line separately and paste the token at its prompt:

```bash
cd ~/pulse-director
umask 077
read -r -s -p 'Developer token: ' EDGE_TOKEN; echo
```

Then run the following **separately** (the token variable exists only in the current shell):

```bash
if [ -n "$EDGE_TOKEN" ]; then
  printf '%s\n' "$EDGE_TOKEN" > .edge_cloud_token
  chmod 600 .edge_cloud_token
  echo 'Token saved'
else
  echo 'Nothing saved: token was empty'
fi
unset EDGE_TOKEN
```

Check permissions without printing the token:

```bash
stat -c '%a %n' .edge_cloud_token
```

Expected permissions are `600`. **Never share the token, a QR image or a copy of `.edge_cloud_token`.**

## 8. Optional cloud control — pair with Cloud Keeper

Stop the dashboard before changing connection settings. In the Pi terminal, replace both values:

```bash
cd ~/pulse-director
EDGE_UID=YOUR_UNIQUE_UID EDGE_PLATFORM='YOUR_EXACT_PLATFORM_NAME' .venv/bin/python edge2_cloud_keeper.py
```

Cloud Keeper uses Lovense's Socket.IO API to maintain the pairing connection. If it needs authorisation, it will create `edge2_service_pairing_qr.png` in the project folder.

If you need to scan it from your PC monitor, in a **separate Windows Command Prompt** copy it from the Pi:

```cmd
scp YOUR_PI_USERNAME@YOUR_PI_IP:/home/YOUR_PI_USERNAME/pulse-director/edge2_service_pairing_qr.png "%USERPROFILE%\Downloads\edge2_service_pairing_qr.png"
```

Open the image locally, then use Lovense Remote's appropriate **Scan QR** function. Keep the keeper process running while pairing. **Don't upload the QR to an issue or share it in chat.** Some versions of the app may require repeated attempts or reauthorisation.

In a second Pi SSH terminal, check status:

```bash
cd ~/pulse-director
python3 -m json.tool .edge_cloud_keeper_status.json
```

Look for `"state": "device_connected"` and `"device_connected": true`. If you see `pairing_qr_ready`, the pairing has not yet been confirmed. **The keeper receives telemetry but does not send motor commands.**

Once paired, start the dashboard with the same UID:

```bash
cd ~/pulse-director
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP --bind YOUR_PI_LAN_IP --uid YOUR_UNIQUE_UID --port 8765 --no-print-key
```

If the phone is reachable on your home LAN, the dashboard will prefer LAN. Away from home, it can select Lovense HTTPS cloud **at session start**, provided Cloud Keeper reports the Edge 2 connected. Stop any active session before changing networks; an interrupted session must not restart automatically.

## 9. Keep the services running after SSH closes (optional)

Only after you have physically verified **Start and Stop** on local and cloud connections, follow [systemd service setup](SERVICES.md). Cloud Keeper and the dashboard need separate systemd services. The example files need your own username, paths, IP addresses, UID and platform name.

## 10. Remote dashboard access through WireGuard

Configure WireGuard (or another **private VPN**) so your phone can access the Pi's private LAN IP. Open `http://YOUR_PI_LAN_IP:8765` **through that VPN**. Do not publish it to the open internet and never give strangers your dashboard access key. **Cloud API connectivity and VPN access are separate:** the VPN reaches the Pi's dashboard, while Lovense's cloud API reaches the phone/device.

## 11. Upgrades and rollback

Back up the current controller, Cloud Keeper, service units and local configuration **privately** before upgrading. An existing installation may use different file paths or service arguments; don't blindly overwrite it with instructions intended for a clean installation. Keep a verified working copy until the new version passes a low-intensity off-body test.

## Next steps

If something doesn't work, see [Troubleshooting](TROUBLESHOOTING.md). Before sharing any logs, remove developer tokens, dashboard access keys, pairing QR details, device IDs and your home IP addresses.