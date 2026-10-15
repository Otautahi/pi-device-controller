# Changelog

## v4.5.0-lan — release candidate

- Kept v4.5 Autonomous Director logic and dashboard interface.
- Removed hybrid cloud backend, pairing monitor and cloud UI states.
- LAN Game Mode remains the only motor command transport.
- Device readiness check rejects zero, multiple and unverified/unsupported connected models.
- No private LAN address or personal path is required in public source.
- Default listening interface is loopback; phone and Pi addresses are runtime arguments.
- Added tests and release documentation.

**Not yet tested with real hardware in this release candidate.**

### Release-candidate QA updates

- Added eight offline regression tests for device identification, rejected Max 2/multiple devices, Stop and expired-command handling, access-key validation and browser security headers (26 tests total).
- Added a separate off-body hardware smoke-test guide. No motor-control code changed during this QA update.
