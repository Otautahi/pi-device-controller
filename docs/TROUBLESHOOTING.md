# Troubleshooting — LAN Edition

This edition only communicates with the **Lovense Remote Game Mode LAN API**; it has no Cloud Keeper or cloud fallback. All examples below use placeholders; do not post your real network addresses or credentials.

## Can't open the dashboard

- The app binds to `127.0.0.1` by default. That is reachable **only from the same machine** (or an SSH tunnel).
- For a browser on another trusted device, start with `--bind YOUR_PI_LAN_IP` and open `http://YOUR_PI_LAN_IP:8765`.
- Make sure the Pi service is still running and that your firewall permits only trusted clients.
- Confirm no other service is already listening on the port. To change it, use `--port 8766` and update the URL accordingly.
- Never expose the HTTP dashboard via router port-forwarding or a public proxy.

## The dashboard asks for an access key

The key is printed when PulseDirector starts. It is also stored in `.edge_dashboard_key` beside the script. Read it **locally on your own Pi**. Never publish the key in a GitHub issue or screenshot. If another person may have obtained it, stop the program and arrange to rotate the key before further use.

## Phone / Game Mode connection failed

- Enable Game Mode inside Lovense Remote on the **same phone paired to Edge 2**.
- Use the **phone's Game Mode IPv4 address** for `--phone`, not the Pi's address.
- Keep the phone on Wi-Fi; avoid guest Wi-Fi/client isolation, restrictive VLAN firewalls and mobile-network-only operation.
- Do not point the app at the cloud API or a developer endpoint; this build uses the phone's port `20010`.
- Never disable network security or expose the dashboard to the internet to work around a connection issue.

## Unknown device or multiple devices rejected

The release candidate deliberately refuses to start when it cannot positively identify **one connected Edge 2**. Disconnect Max 2 and any other toys. If your Edge 2 is reported under an unexpected model name, do **not** bypass validation. Report only a sanitized, non-identifying description of the model fields and firmware.

## Red fault warning / automatic Stop pending

A detected Bluetooth/Wi-Fi/Game Mode failure ends the session and attempts Stop. If the phone or toy cannot receive the command, the dashboard **cannot verify physical inactivity**. Keep the device off-body during tests and power it off physically if it continues vibrating. Once exactly one Edge 2 reconnects, the controller retries Stop. The red warning intentionally stays visible until the phone API has accepted recovery Stop commands and you **check the physical toy and acknowledge**. A brief vibration can occur on Bluetooth reconnection before the Stop reaches the toy. Do not bypass this fault latch. If the warning stays pending, check Game Mode, Bluetooth and Wi-Fi; do not assume the 00:00 timer means physical Stop.

## Director doesn't start, or Stop seems delayed

- Check the session timer, maximum intensity cap and whether the device is actually connected.
- A simulated test checks software behaviour, not the real Bluetooth link.
- A failed network or Bluetooth connection can prevent delivery of Stop; **physically disconnect or turn off the device** immediately when required.
- Do not treat a command counter, API 200 response or stale telemetry as evidence that physical motion occurred.
- An interrupted session should never be resumed without a deliberate fresh Start.

## Asking for help safely

For issues, include the application version, Python version, whether you're using `--simulate`, and steps to reproduce. **Remove** phone/Pi IPs, usernames, private file paths, dashboard keys, device IDs, pairing QR data, timestamps linked to your activity and authentication headers. Never attach raw working-directory backups or private runtime logs.
