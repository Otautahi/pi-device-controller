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
