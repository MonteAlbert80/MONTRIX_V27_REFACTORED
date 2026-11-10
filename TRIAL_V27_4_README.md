# Montrix 27.4 controlled trial — important safety warning

This is a source + deployment orchestration package. No compiled APK is included. It was NOT compiled against Android SDK or tested on the FYT head unit.

## Existing car observations
- Speed showed 0 while driving; speed limit and temperature displayed `--`.
- Music remained silent until switching to radio and back.
- RDS appeared to work well.
These are manual baseline observations, NOT automated ADB passes/fails. Do not interpret a zero penalty as no defects.

## Safety gates
- `baseline` captures APK, validated private-data TAR, and ADB evidence; it does NOT install.
- `deploy` requires explicit `-TrialConsent -AllowUnsafeRollback` because Android downgrade and hardware behavior cannot be proved in advance. This is a high-risk override, not an assurance of safe rollback.
- The deployment retains APK and data backups and will attempt APK downgrade on a rejected score. Android may reject the downgrade; app data restoration is not automated.
- The regression score can fail to improve even if a visible bug was fixed, because uninstrumented tests are UNKNOWN. Expect conservative rejection.
- Use a NEW results directory per trial; never overwrite the known-good backup.
- No automatic uninstall, data clear, or destructive rollback is performed.

## Commands
First baseline (no changes):
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode baseline -device '192.168.1.159:5555' -Results 'D:\ASURE\MONTRIX_TRIAL_20261105'
```
The baseline command creates a backup; do not reuse the same results directory for `deploy` with this version because it refuses to overwrite an existing backup. To conduct a trial, use a new directory and run `deploy` directly; it captures its own baseline first.

**Risk-acknowledged trial, only if you accept possible failure to roll back:**
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode deploy -device '192.168.1.159:5555' -Results 'D:\ASURE\MONTRIX_TRIAL_DEPLOY_01' -TrialConsent -AllowUnsafeRollback
```

Manual rollback (same results directory):
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode rollback -device '192.168.1.159:5555' -Results 'D:\ASURE\MONTRIX_TRIAL_DEPLOY_01'
```

## Why a guaranteed blue/green swap is unavailable
Both APK versions use `com.monte.cwgradio`. Android cannot install both versions simultaneously under the same package ID. On an unrooted device, `adb install -r -d` may reject an older version and private app data cannot be safely restored through ordinary ADB after schema migrations. True rollback requires a tested version-compatible fallback or privileged backup/recovery.

## Known harness limitations
ADB does not verify speaker output, true FM frequency, actual RDS content, ignition sleep behavior, real GPS speed, speed limits, or CAN temperature without dedicated in-app instrumentation and physical testing. These remain UNKNOWN and cannot justify automated promotion.
