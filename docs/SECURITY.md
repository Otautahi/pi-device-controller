# Security and privacy

The dashboard controls a physical device. Use it **only on a trusted LAN or appropriately configured private VPN**. It listens on loopback by default. If binding to a LAN interface, restrict network access to trusted clients; never forward the port to the public internet. The interface uses HTTP and a shared dashboard key rather than TLS; untrusted LAN users could potentially intercept traffic.

## Files and credentials

- `.edge_dashboard_key` is generated locally with owner-only permissions, and is not included in the source ZIP. Do not expose it in screenshots, GitHub commits, bug reports or application logs.
- No cloud token, pairing QR, private UID, device identifier, hardcoded private network address, systemd unit or backup from the owner's Pi is included.
- `.gitignore` cannot undo historic commits containing secrets. Rotate leaked secrets, and remove sensitive objects from public Git history before publication.

## Device safety

> **Bluetooth reconnect remains an inherent risk:** In the original build, Bluetooth loss led to code 402 / 00:00, then continuous vibration on reconnect. In the updated build, one owner-observed off-body test showed **brief resumed vibration followed by automatic Stop**; the fault warning blocked new sessions until recovery and acknowledgement. **Automatic Stop cannot be delivered while Wi-Fi/Bluetooth is unavailable and is not a physical fail-safe.** Keep the physical power button accessible. See [issue #2](https://github.com/Otautahi/pulse-director/issues/2) and [recovery design](RECOVERY_DESIGN.md).

- Only an `Edge`/`Edge 2` device reported connected by Game Mode is accepted; ambiguous/unsupported reports cause a refusal to start. Device detection was tested on one Edge 2; Bluetooth reconnect was mitigated in one controlled off-body test but brief unintended vibration remains.
- Start with the device off-body and low intensity. Keep a direct physical stop option.
- The app transmits bounded, short-duration commands and attempts Stop on errors, expiry and shutdown, but cannot guarantee immediate physical Stop after phone, Bluetooth or network failure.
- A new session requires a fresh device readiness check; the controller never deliberately resumes a previous one after a detected error.
- Dashboard command counts are not proof of physical vibration.

## Disclosure and compliance

This project is independent and unaffiliated with Lovense. Public distribution via GitHub is **not cleared for a stable release**: section 3.5 of the [Application Developer and API Agreement](https://www.lovense.com/app-develop-api) restricts third-party public-code repositories unless distribution conditions are met. [Issue #4](https://github.com/Otautahi/pulse-director/issues/4) tracks written permission/clarification. The source's MIT licence does not override Lovense's separate API, app or developer-material terms.
