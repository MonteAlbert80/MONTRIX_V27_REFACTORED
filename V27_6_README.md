# Montrix v27.6 — measured trial hold

- Read-only QA snapshot reports process ID, GPS provider enablement, Android music-active status, music volume and preset preference count. These are diagnostic indicators, NOT proof of speaker sound, GPS fixes, CAN temperature, RDS, speed-limit lookup, or successful tuning.
- Deployment performs verified APK/private-data backup, builds, installs and checks critical regressions. If a regression is detected it attempts verified APK rollback. If none is detected, candidate remains installed in **AWAITING_MANUAL_HARDWARE_ACCEPTANCE**; it is NOT automatically accepted.
- Manual rollback command remains available. APK rollback is not equivalent to verified private-data restoration. `-AllowUnsafeRollback` explicitly authorizes that risk.
- Regression testing never changes tuner or music mode; only snapshot query is sent.
- Use a fresh `-Results` directory for each trial. Park before testing controls; never evaluate while driving.
- Device must be reachable; deployment script explicitly runs `& $Adb connect $device`.
