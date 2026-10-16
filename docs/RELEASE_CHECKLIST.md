# Release checklist — v4.5.0 LAN Edition

## Public source branch — completed

- [x] Keep the running private PulseDirector installation separate from the public source
- [x] Remove cloud API, Cloud Keeper, cloud pairing, tokens and cloud UI states from this edition
- [x] Remove personal network addresses and absolute installation paths from the published source
- [x] Include LAN-only Edge 2 model checks that reject zero, multiple and unsupported device reports
- [x] Run the original **18 offline tests** successfully on the owner's Pi
- [x] Add **8 more offline safety regressions** (26 tests total); pass in GitHub Actions on Python 3.11 and 3.13
- [x] Run the GitHub Actions offline test matrix successfully on the public candidate branch
- [x] Add README, installation and security guidance, changelog and MIT licence
- [x] Obtain owner's approval to publish the source branch
- [x] Push candidate to public branch `release/v4.5.0-lan-rc1`
- [x] Open [draft pull request #1](https://github.com/Otautahi/pulse-director/pull/1) against `main`

**Reminder:** The public source branch is already publicly accessible. A draft PR does not make it private.

## Before merging into `main`

**MERGE BLOCKED:** [Issue #2](https://github.com/Otautahi/pulse-director/issues/2) — observed unintended vibration after Bluetooth reconnect. Do not merge or tag until resolved and explicitly approved.

- [ ] Complete final review of source, Git history, release assets, generated screenshots and identifying metadata
- [ ] Verify copyright attribution and third-party distribution/API requirements
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
- [x] **Concurrent Stop/Start and Stop/motor-test** offline regression tests added; all 39 tests pass on Python 3.11 and 3.13 and on owner's Pi.
- [ ] **Before release:** review residual brief Bluetooth reconnect vibration, verify relevant vendor terms, fresh-install and final code security review; obtain explicit merge/release approval. The dashboard cannot guarantee physical Stop during disconnection.
- [ ] Test simultaneous/concurrent Start and Stop requests and physical disconnect fallback
- [ ] Confirm UI telemetry and simulated-status labels are not misleading
- [ ] Verify updated install documentation on supported fresh Raspberry Pi OS
- [ ] Approve release notes, supported hardware statement and version tag
- [ ] Obtain explicit owner approval for a stable release

Passing automated tests does **not** certify physical motor control or a guaranteed emergency stop. Never upload a live controller directory, access key, cloud token or personally identifying logs.
