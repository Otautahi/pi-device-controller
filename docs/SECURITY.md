# Security and privacy

The dashboard controls a physical device. Use it **only on a trusted LAN or appropriately configured private VPN**. It listens on loopback by default. If binding to a LAN interface, restrict network access to trusted clients; never forward the port to the public internet. The interface uses HTTP and a shared dashboard key rather than TLS; untrusted LAN users could potentially intercept traffic.

## Files and credentials

- `.edge_dashboard_key` is generated locally with owner-only permissions, and is not included in the source ZIP. Do not expose it in screenshots, GitHub commits, bug reports or application logs.
- No cloud token, pairing QR, private UID, device identifier, hardcoded private network address, systemd unit or backup from the owner's Pi is included.
- `.gitignore` cannot undo historic commits containing secrets. Rotate leaked secrets, and remove sensitive objects from public Git history before publication.

## Device safety

- Only an `Edge`/`Edge 2` device reported connected by Game Mode is accepted; ambiguous/unsupported reports cause a refusal to start. This safety check is **not hardware-validated**.
- Start with the device off-body and low intensity. Keep a direct physical stop option.
- The app transmits bounded, short-duration commands and attempts Stop on errors, expiry and shutdown, but cannot guarantee immediate physical Stop after phone, Bluetooth or network failure.
- A new session requires a fresh device readiness check; the controller never deliberately resumes a previous one after a detected error.
- Dashboard command counts are not proof of physical vibration.

## Disclosure and compliance

This project is independent and unaffiliated with Lovense. Check vendor API licensing and redistribution permissions before a public tagged release. The source is distributed under MIT; that does not override Lovense's separate developer/API terms.
