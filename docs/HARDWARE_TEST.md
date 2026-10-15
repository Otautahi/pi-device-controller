# Edge 2 hardware smoke test — v4.5.0 LAN RC1

**Status:** not yet completed. This guide checks the *published LAN-only build*, not the owner's working hybrid controller. Perform all motor tests **off-body**, with the device in reach and the ability to turn it off physically.

## Before testing

- Stop any active session in any other dashboard/controller. **Never run two controllers' motor sessions against the same phone/toy simultaneously.**
- Ensure just **one Edge 2** is connected in Lovense Remote; disconnect Max 2 and any other Lovense devices.
- Enable **Game Mode** in Lovense Remote and note the phone's local IPv4 address. Use a trusted LAN.
- Confirm the published candidate is in its **own directory**, not the existing live installation.
- Do not send IP addresses, access keys, device identifiers or unredacted logs to GitHub or ChatGPT.

## Set up on the Raspberry Pi

If you have not cloned the candidate already:

```bash
cd ~
git clone --branch release/v4.5.0-lan-rc1 --single-branch \
  https://github.com/Otautahi/pulse-director.git pulse-director-lan-test
```

Run the offline tests (currently 26 tests across the suite):

```bash
cd ~/pulse-director-lan-test
python3 --version
python3 -m unittest discover -s tests -v
```

While your private dashboard occupies port `8765`, run the candidate on **port `8766`**. Replace the placeholders with the addresses shown **locally** on your own devices:

```bash
python3 edge_dashboard.py --phone YOUR_PHONE_LAN_IP \
  --bind YOUR_PI_LAN_IP --port 8766
```

Open `http://YOUR_PI_LAN_IP:8766` in a browser on your trusted LAN and enter the candidate's **separately generated** dashboard key. Keep that key private.

> If the port is unavailable, choose another unused LAN-only port. Do not router-forward any dashboard port or expose the plain-HTTP interface publicly.

## Five-minute off-body checklist

- [ ] **Detection:** dashboard identifies one connected Edge 2. If it rejects the device model, **stop here**; do not bypass verification.
- [ ] **Motor 1:** low-intensity manual setting activates only Motor 1 as expected.
- [ ] **Motor 2:** low-intensity manual setting activates only Motor 2 as expected.
- [ ] **Stop:** Stop ends motor activity promptly. Keep the physical shutoff accessible.
- [ ] **Timeout:** start a short session (minimum 0.25 min = 15 seconds); confirm it ends and motors cease.
- [ ] **Director:** briefly start Autonomous Director at a low cap, observe intent/status, then press Stop.

Optional, **only after the above works** and with the device off-body: disrupt phone Wi-Fi or Bluetooth and verify the dashboard stops attempting the session; physically switch the toy off if Stop cannot reach it. A network outage may prevent remote Stop delivery.

## Finish safely

Press Stop in the web UI, turn the device off, and stop the candidate server with **Ctrl+C**. Your private hybrid installation and its service should remain unchanged.

## How to report the results

Share only a sanitized summary, for example:

```text
LAN RC1 hardware check
- Python version: 3.x
- Device detection: PASS / FAIL
- Motor 1: PASS / FAIL
- Motor 2: PASS / FAIL
- Stop: PASS / FAIL
- 15-second expiry: PASS / FAIL
- Autonomous Director: PASS / FAIL
- Connection interruption (optional): PASS / FAIL / NOT TESTED
- Notes: (no keys, IP addresses, toy IDs or raw logs)
```

Even a passing off-body smoke test does **not** certify a guaranteed emergency stop or comprehensive firmware compatibility. See [Security](SECURITY.md) and the [release checklist](RELEASE_CHECKLIST.md).
