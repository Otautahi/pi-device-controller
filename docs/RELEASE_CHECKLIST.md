# Release checklist — v4.5.0 LAN Edition

## Public source branch — completed

- [x] Keep the running private PulseDirector installation separate from the public source
- [x] Remove cloud API, Cloud Keeper, cloud pairing, tokens and cloud UI states from this edition
- [x] Remove personal network addresses and absolute installation paths from the published source
- [x] Include LAN-only Edge 2 model checks that reject zero, multiple and unsupported device reports
- [x] Run the original **18 offline tests** successfully on the owner's Pi
- [x] Add 8 safety regression tests (26 total initially), then 8 recovery tests and 5 concurrency tests (**39 total**), passing in GitHub Actions across Python 3.10–3.13
- [x] Run the GitHub Actions offline test matrix successfully on the public candidate branch; **39 tests each on Python 3.10/3.11/3.12/3.13** (17 October 2026)
- [x] Add README, installation and security guidance, changelog and MIT licence
- [x] Obtain owner's approval to publish the source branch
- [x] Push candidate to public branch `release/v4.5.0-lan-rc1`
- [x] Open [draft pull request #1](https://github.com/Otautahi/pulse-director/pull/1) against `main`

**Reminder:** The public source branch is already publicly accessible. A draft PR does not make it private.

## Before merging into `main`

**MERGE / STABLE TAG ON HOLD:** The persistent Bluetooth reconnect failure in [issue #2](https://github.com/Otautahi/pulse-director/issues/2) was mitigated, but **brief vibration still occurs before automatic Stop**. The separate release gate is [issue #4](https://github.com/Otautahi/pulse-director/issues/4): Lovense's [API agreement](https://www.lovense.com/app-develop-api), sections 1.3 and 3.5, raises an unresolved restriction on publication in public code repositories. The source candidate is already public; that does not establish redistribution permission.

- [ ] Complete final review of source, Git history, release assets, generated screenshots and identifying metadata
- [ ] **Blocking:** confirm Lovense API/public GitHub redistribution rights in writing or with qualified legal guidance ([issue #4](https://github.com/Otautahi/pulse-director/issues/4)); independently confirm copyright/source attribution
- [ ] Check fresh-install steps on a clean supported Pi/Linux setup
- [x] Approve and upload **simulation-labelled** LAN desktop/mobile screenshots
- [x] Set appropriate `main` branch protection / repository ruleset and required CI checks
- [ ] Review the final PR diff and explicitly approve merging

## Before a stable GitHub Release

- [x] Follow the [off-body hardware test guide](HARDWARE_TEST.md) for basic detection, motor, Stop and timeout tests; record sanitized results (16 October 2026)
- [x] Confirm live **GetToys** response identifies one Edge 2 on the owner's current hardware/app combination (16 October 2026)
- [x] Verify both motors, live Stop, autonomous operation and 30-second timer expiry **off-body** (owner-reported; 16 October 2026)
- [x] Test **phone Wi-Fi interruption/reconnection** during an active session; owner reported immediate motor stop and no automatic restart on reconnect (16 October 2026)
- [x] **Mitigation retested on fix branch (16 October 2026):** Original build had persistent vibration after Bluetooth reconnect (Lovense 402); fix branch observed brief reconnect vibration followed by **automatic Stop**, fault warning and successful manual acknowledgement. [Issue #2](https://github.com/Otautahi/pulse-director/issues/2) remains open for residual risk and broader validation.
- [x] **Wi-Fi retested on updated fix branch (17 October 2026):** motors stopped on Wi-Fi loss and stayed stopped after reconnection; automatic Stop recovery completed; acknowledgement restored controls (owner-reported).
- [x] **Concurrent Stop/Start and Stop/motor-test** offline regression tests added; all 39 tests pass on Python 3.10–3.13 in GitHub Actions and on owner's Pi.
- [ ] **Before release:** review residual brief Bluetooth reconnect vibration, verify relevant vendor terms, fresh-install and final code security review; obtain explicit merge/release approval. The dashboard cannot guarantee physical Stop during disconnection.
- [x] Test simulated concurrent Start/Stop requests in deterministic offline regressions (5 tests)
- [ ] Validate simultaneous Start/Stop and physical disconnect fallback on hardware if safely possible
- [x] Confirm that the UI labels successful Stop as **phone API acknowledgement**, not a physical measurement, and explicitly indicates unknown physical state after fault
- [ ] Perform final UI accessibility/telemetry review on a fresh supported setup
- [x] Correct installation docs to reflect 39 tests, hardware recovery and remaining risk
- [ ] Verify a completely fresh Raspberry Pi OS install outside the owner's existing directories
- [x] Draft updated changelog and explicitly limit supported hardware to one Edge 2
- [ ] Approve final version tag/release title and stable-release notes after legal clearance
- [ ] Obtain explicit owner approval for a stable release

Passing automated tests does **not** certify physical motor control or a guaranteed emergency stop. Never upload a live controller directory, access key, cloud token or personally identifying logs.
