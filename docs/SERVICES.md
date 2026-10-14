# Optional background services (systemd)

> **Advanced step.** Do this only after testing Start and Stop off-body in both local and optional cloud modes. Service templates are for a **new installation**, not drop-in replacements for an existing working dashboard.

Both processes use the **same project directory**: the dashboard controls the Edge 2 while Cloud Keeper maintains pairing and reports last-seen telemetry. Neither process should run as root.

## 1. Edit the sample files

On your Linux host, from the newly cloned `~/pulse-director` directory:

```bash
cp examples/edge2-dashboard.service.example edge2-dashboard.service
cp examples/edge2-cloud-keeper.service.example edge2-cloud-keeper.service
nano edge2-dashboard.service
nano edge2-cloud-keeper.service
```

Replace **every** placeholder: Linux username, project directory, phone's Game Mode IP, Pi's private IP, and the unique UID. The dashboard's `--uid` must equal the keeper's `EDGE_UID`; `EDGE_PLATFORM` must exactly match the registered Lovense platform name.

Keep the token only in `.edge_cloud_token`. Never paste it into the service unit. Use `--no-print-key` to avoid logging the dashboard access key.

If you use only local LAN control, install **only** the dashboard service (without a cloud token and `--uid`), and skip Cloud Keeper.

## 2. Copy service units into systemd

```bash
sudo cp edge2-dashboard.service /etc/systemd/system/edge2-dashboard.service
```

For cloud users only:

```bash
sudo cp edge2-cloud-keeper.service /etc/systemd/system/edge2-cloud-keeper.service
```

Then:

```bash
sudo systemctl daemon-reload
```

## 3. Enable cloud first (cloud users only)

```bash
sudo systemctl enable --now edge2-cloud-keeper
sudo systemctl status edge2-cloud-keeper --no-pager
```

If the keeper needs QR authorisation, see [installation guide §8](INSTALL.md#8-optional-cloud-control--pair-with-cloud-keeper).

## 4. Enable the dashboard

Make sure no other dashboard process is listening on port `8765`. Then:

```bash
sudo systemctl enable --now edge2-dashboard
sudo systemctl status edge2-dashboard --no-pager
```

Check that both processes run as your ordinary Pi user and are configured for your private LAN. Test a short low-intensity session and manual Stop with the device **off-body**.

## 5. Operate and troubleshoot

```bash
sudo systemctl restart edge2-dashboard
sudo systemctl stop edge2-dashboard
sudo systemctl status edge2-dashboard edge2-cloud-keeper --no-pager
sudo journalctl -u edge2-dashboard -n 30 --no-pager
```

A service reporting `active (running)` does **not** prove the device is connected. Cloud Keeper's `device_connected` status and a physical low-intensity test are separate checks.

## 6. Reboot and updates

Restarting or rebooting can interrupt pairing and may require another QR authorisation. Do not assume a session will survive a reboot. Keep backup copies of the controller and your edited service units, and never overwrite an existing production installation without a tested rollback route.