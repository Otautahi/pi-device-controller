# Contributing

PulseDirector is an independent hobby project. Please keep contributions small, explain why a change is needed and include offline tests when modifying the controller.

## Before opening an issue or pull request

- Use the public `release/v4.5.0-lan-rc1` branch or an up-to-date feature branch; keep `main` protected.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m py_compile edge_dashboard.py edge2_director.py`.
- Test without connecting any physical device first. **Never** test new control logic on-body.
- Do not claim live hardware compatibility without clearly describing an off-body test and supported firmware.
- Preserve intensity caps, physical Stop guidance, timer bounds and per-device validation.
- Keep vendor cloud APIs, credentials and pairing files out of this LAN-only edition.
- No change should cause a session to restart automatically after losing connectivity.

## Safe issue reports

Include the application version, Python version, minimal steps to reproduce and *sanitized* error text. Never attach dashboard keys, cloud tokens, device identifiers, unredacted command responses, private IPs, physical addresses, pairing QR codes, logs from active sessions or copies of a private runtime folder.

## Scope

The current public build supports **only one Edge 2**. Max 2 or multi-device contributions need separate, explicit testing and review rather than relaxing existing device validation. See the [release checklist](docs/RELEASE_CHECKLIST.md).
