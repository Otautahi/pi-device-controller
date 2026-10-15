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

- [ ] Complete final review of source, Git history, release assets, generated screenshots and identifying metadata
- [ ] Verify copyright attribution and third-party distribution/API requirements
- [ ] Check fresh-install steps on a clean supported Pi/Linux setup
- [ ] Approve and upload **simulation-labelled** LAN desktop/mobile screenshots
- [ ] Set appropriate `main` branch protection / repository ruleset and required CI checks
- [ ] Review the final PR diff and explicitly approve merging

## Before a stable GitHub Release

- [ ] Follow the [off-body hardware test guide](HARDWARE_TEST.md) and record sanitized pass/fail results
- [ ] Confirm live **GetToys** response identifies Edge 2 on actual firmware
- [ ] Physically verify both motors, independent Stop, manual mode and timer expiry **off-body**
- [ ] Test loss/recovery of Wi-Fi, Bluetooth and phone connectivity; ensure no uncommanded restart
- [ ] Test simultaneous/concurrent Start and Stop requests and physical disconnect fallback
- [ ] Confirm UI telemetry and simulated-status labels are not misleading
- [ ] Verify updated install documentation on supported fresh Raspberry Pi OS
- [ ] Approve release notes, supported hardware statement and version tag
- [ ] Obtain explicit owner approval for a stable release

Passing automated tests does **not** certify physical motor control or a guaranteed emergency stop. Never upload a live controller directory, access key, cloud token or personally identifying logs.
