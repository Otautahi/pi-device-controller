# LAN Edition public release checklist

- [x] Split working copy from Pi's installed controller; do not touch existing services
- [x] Strip all cloud-specific classes, routes, token files and UI diagnostics
- [x] Remove Pi-specific default addresses, usernames and absolute service paths
- [x] Add local device validation and reject multiple / unsupported devices
- [x] Add offline unit and simulated HTTP tests
- [ ] Test live GetToys model/status formats on actual Edge 2 firmware; fix incompatibilities
- [ ] Test Motor 1, Motor 2, independent Stop and timed expiry off-body
- [ ] Test connection-loss behaviour and recovery, including concurrent Start/Stop
- [ ] Confirm independent physical stop remains available after Wi-Fi / Bluetooth loss
- [ ] Confirm the published files, screenshots, docs and *history* contain no secrets or personal IP addresses
- [x] Add an MIT licence to the GitHub-ready candidate (verify copyright attribution with owner)
- [ ] Check Lovense third-party API redistribution / usage terms
- [ ] Review README and test instructions on clean Raspberry Pi OS installation
- [ ] Obtain project owner's explicit approval before a public GitHub push/tagged release

**Do not publish the original working installation directory.**
