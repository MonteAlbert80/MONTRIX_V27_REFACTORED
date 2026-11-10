# Montrix v27.3 — ADB connection + report review

`MONTRIX_DEPLOY.ps1` now accepts `-device`, defaulting to `192.168.1.159:5555`. It executes `& $Adb connect $device`, checks `adb devices` for an online match, then passes the device as `--serial` to the Python regression runner. `-Serial` remains a backward-compatible alias.

## Run safe baseline

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\ASURE\MONTRIX_V27_REFACTORED\MONTRIX_DEPLOY.ps1" -Mode baseline -device '192.168.1.159:5555'
```

## Report (Nov 5, 2026)

- Installed versionCode 261600 (v26.16.0).
- APK backup SHA256 3817f009ff5589a5fb4a05f97ff803b70f3e9583d3757975886c2109c0197b1e.
- Valid 7168-byte private-data TAR with five shared preference XML files.
- Ten passes, one warning, thirteen unknowns. No verified radio/preset/sleep-wake behavior.
- No candidate deployed. Do not deploy automatically based on zero failure penalty: coverage remains inadequate.
- Backup is structurally valid, but rollback installation and private-data restoration have NOT been tested.
