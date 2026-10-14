# Security and privacy

PulseDirector can operate a physical device. Treat the ability to log into the dashboard as control access, and take particular care before making any code or screenshots public.

## Protect access

- Keep the dashboard restricted to a **trusted home LAN** or a **private VPN** such as WireGuard. It uses **HTTP, not HTTPS**. Never forward/open port `8765` on your router to the internet.
- Use a unique dashboard access key; keep `.edge_dashboard_key` permission `0600`. Don't put it into URLs, screenshots or GitHub issues.
- Keep `.edge_cloud_token` permission `0600`. Never include it in a repository, issue, log, photo or public installer. Your Lovense token is a credential, not a setting to share.
- Pairing QR codes and the status file are private runtime artifacts. Delete unnecessary exported QR copies from your Windows Downloads folder.
- Create your own unique UID and developer-platform registration. Don't publish the UID, QR payload, device IDs or any personal network details.

## Protect the device

- **Only the Lovense Edge 2 is supported.** Disconnect other devices before use. The release candidate rejects unexpected/multiple devices in reported data, but this has not been exhaustively tested with every firmware and connection combination.
- Start with an off-body, low-intensity test. Keep an independent physical way to disconnect/stop the toy.
- Stop and timed commands are **best effort** over Bluetooth, phone and cloud links. A network outage may prevent immediate Stop delivery. The user remains responsible for the physical device.
- Do not deploy an untested change while a session is active. A dropped connection should never silently restart a prior session.

## Keep GitHub clean

- Never upload the working Pi directory wholesale. Publish only a reviewed source-only copy.
- `.gitignore` excludes common secrets and build files, but it **cannot guarantee safety**. Always inspect `git status` and staged diffs before committing.
- If a token or key is committed, revoke/rotate it immediately. Removing it in a future commit is **not** enough: Git history may still contain it.
- GitHub account names and commit author information can be public even when source files are anonymised. The repository is intentionally hosted under `Otautahi`.
- Do not put private IP addresses, home addresses, device IDs, login screenshots or unredacted logs in public issues.

## Legal and service considerations

This independent project is not affiliated with Lovense. Developer APIs and third-party distribution are governed by Lovense's rules and can change. Confirm whether developer registration and API access permit a public application before issuing a first release.
