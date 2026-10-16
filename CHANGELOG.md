# Changelog

## v4.5.0 LAN Edition — experimental release candidate (17 October 2026)

**Not a stable release.** `main` merge and stable tagging await final owner approval, fresh-install validation and further safety review. [Issue #4](https://github.com/Otautahi/pulse-director/issues/4) records an unresolved question about whether Lovense's API-publication terms apply to independent LAN Game Mode GitHub projects; it is a clarification item, not proof of a blanket ban. Source on the candidate branch is already public.

### Functionality
- Retained the v4.5 Autonomous Director and browser dashboard for **one Edge 2** using the phone's local Game Mode API.
- Removed the private hybrid/cloud backend, pairing monitor, Cloud Keeper, cloud UI states and credentials.
- Added explicit device checks that reject zero, multiple or unverified/unsupported connected devices, including Max 2.
- Default loopback HTTP bind and generated local access key; runtime phone and Pi addresses are not embedded in source.

### Connection recovery and Stop priority
- On detected Wi-Fi/Bluetooth/Game Mode failure, invalidate the session and attempt Stop immediately.
- When unreachable, latch a **physical state unknown** warning; retry Stop automatically after exactly one Edge 2 reconnects and require user acknowledgement before further motor activity.
- Send multiple distinct Stop requests after reconnection; these confirm **phone API replies only**, not physical motor state.
- Explicit Stop now cancels in-flight Start, motor Test and pattern-switch validation, preventing a stale request from reactivating motors.
- Added eight recovery regression tests, five concurrent Stop/Start tests and a malformed-response safety regression: **40 offline tests** total.

### Owner-reported off-body tests
- Basic detection, both motors, Director, timed session and manual Stop passed (16 October 2026).
- Original candidate **failed** Bluetooth reconnect: vibration returned and persisted until manual Stop.
- **Updated candidate:** Bluetooth reconnect caused **brief vibration** followed by **automatic Stop** without manual action; a red fault lock appeared and cleared on operator acknowledgement (16 October 2026).
- Updated candidate Wi-Fi disconnect/reconnect: motors stayed stopped, recovery completed and acknowledgement restored controls (17 October 2026).
- GitHub Actions passed all 40 tests on Python 3.10–3.13; the owner ran the preceding 39-test version on the Pi.

**Limitations:** neither short timed commands nor automatic retries guarantee physical Stop when communication is lost; brief vibration may occur on reconnection. The hardware results cover one user's setup only, not independent certification or broad device/firmware compatibility. See [issue #2](https://github.com/Otautahi/pulse-director/issues/2) and [recovery design](docs/RECOVERY_DESIGN.md).
