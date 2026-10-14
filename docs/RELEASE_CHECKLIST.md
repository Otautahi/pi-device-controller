# First release checklist (not yet published)

- [ ] Confirm only an Edge 2 is connected and unknown/Max 2/multiple devices are refused on LAN and cloud
- [ ] v4.2 tested on actual Edge 2 after upgrade (two independent motors, Start and Stop)
- [ ] Autonomous Director run off-body at low intensity with multiple patterns
- [ ] 20-minute automatic stop and emergency Stop physically verified
- [ ] Home Wi-Fi to cloud switching verified; cloud requires pairing/online session
- [ ] Connection-loss handling physically tested; no unexpected restart on reconnect
- [ ] Battery UI checked and stale values clearly explained
- [ ] Pi-hole, WireGuard and other background services unaffected
- [ ] No private values in source: IP, API token, password, personal UID, device IDs, QR, logs, backup files
- [ ] Confirm GitHub repository owner and Git commit author metadata are acceptable publicly (cannot hide a personal account via source scrubbing)
- [ ] Optional wishlist checked from an incognito/public buyer view; no identifying address/name details
- [ ] `.gitignore`, staged contents and Git history reviewed for leaks
- [ ] Documentation checked by someone who has not installed the software before
- [ ] Confirm Lovense API/distribution requirements for non-personal users
- [ ] Confirm MIT licence and chosen public project name
- [ ] GitHub release/commit only after owner's go-ahead

Do not publish the live contents of the Raspberry Pi's `~/edge-ai` directory.