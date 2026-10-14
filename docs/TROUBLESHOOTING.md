# Troubleshooting

These checks are for the **Edge 2-only** release candidate. Commands labelled **Pi** run in an SSH session on your Linux host (originally tested on a Raspberry Pi); those labelled **Windows** run on your PC.

## Dashboard doesn't open

Check on the **Pi**:

```bash
sudo systemctl status edge2-dashboard --no-pager
```

If you are running it interactively, the SSH terminal must remain open. Use the exact private IP passed in `--bind`, and connect from the same trusted network or your private VPN. Check port `8765` is not already occupied (`ss -ltn | grep ':8765'`). **Do not forward the port on your router.**

## Dashboard says device unavailable on home Wi-Fi

Check Lovense Remote Bluetooth, Edge 2 selection, Game Mode LAN, and the **current phone Wi-Fi IP**. Game Mode's local IP may change after reconnection. On the Pi, replace the example address with the phone IP shown in Game Mode:

```bash
curl -sS --max-time 8 -H 'Content-Type: application/json' -H 'X-platform: Pi-Edge-Dashboard' \
  --data '{"command":"GetToys"}' http://YOUR_PHONE_LAN_IP:20010/command
```

This reads device information and does **not** activate motors. Check the JSON for an Edge 2 and the API status. If multiple toys appear, disconnect all but Edge 2.

## The dashboard opens remotely but the device doesn't respond

Opening the dashboard over VPN does **not** mean Game Mode's local API is reachable on mobile data. The optional cloud method depends on your own developer token, a connected Cloud Keeper and a paired Lovense Remote session.

On the **Pi**:

```bash
sudo systemctl status edge2-cloud-keeper --no-pager
python3 -m json.tool ~/pulse-director/.edge_cloud_keeper_status.json
```

`device_connected: true` is the expected paired state. `pairing_qr_ready` means authorisation is still pending. A missing or stale status can mean Cloud Keeper is stopped or disconnected. **Do not share the status file unredacted.**

## Cloud API returns code 507

This was observed when Lovense considered the paired app offline. Open Lovense Remote and confirm the Edge 2 is connected, and verify Cloud Keeper is still reporting a paired online device. The server may require re-pairing. A token file being present is **not** proof that the app is reachable.

## Cloud authentication returns 403 / Cloudflare 1010

Some Python HTTP clients may be blocked by Cloudflare although `curl` succeeds. This project uses `curl` for the cloud API. A `curl` request reporting a Lovense JSON error is different from a Cloudflare block. Do not disable security protections or share your developer token to troubleshoot.

## QR code is unreadable or rejected

Make sure the QR was generated for the **currently running Cloud Keeper session**, not copied from an old script or previous demo. The code can expire or its session may have ended. Keep the keeper running while scanning from a second screen, and check the Lovense Remote scanner supports third-party/game integrations. Do not publish the QR or raw pairing payload.

## `ImportError: libopenjp2.so.7`

On Raspberry Pi OS, try:

```bash
sudo apt install -y libopenjp2-7
```

Then retry importing Pillow through the project virtual environment.

## Wrong device, unsupported model, or multiple connected devices

This release accepts **one Edge 2 only**. Max 2 and other models are deliberately unsupported. Disconnect other toys, restart the relevant controller process, and confirm Lovense Remote reports Edge 2. **Do not disable the model guard to make an unknown device work.**

## Battery level jumps between LAN and cloud

Cloud Keeper stores a **last reported** battery value, which may be stale. The value obtained through LAN may be newer. The app's direct reading is preferable when checking current charge. Check timestamps; a cloud number changing back after a route switch does not mean the device actually recharged.

## Stop didn't arrive immediately

The device or phone may have become unreachable. Use a **physical way to disconnect the device** and ensure no session is still running. Timed motor commands are a secondary safeguard, not guaranteed emergency-stop delivery. Don't continue testing until you understand the connection problem.

## How to collect useful logs safely

On the Pi:

```bash
sudo systemctl status edge2-dashboard edge2-cloud-keeper --no-pager
sudo journalctl -u edge2-dashboard -n 30 --no-pager
sudo journalctl -u edge2-cloud-keeper -n 30 --no-pager
```

**Before sharing:** remove tokens, access keys, QR URLs and contents, device identifiers, user IDs, network addresses and any personal details. Never post the whole contents of `~/pulse-director` or your home Pi installation.