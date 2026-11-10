# Montrix Blue/Green — ADB-first, fail-closed candidate

## Reality check
ADB (not "ADP") can collect logs, control activities, query services, pull APKs and run debug QA endpoints. It **cannot prove** radio sound, RDS correctness, ignition sleep behavior, GPS accuracy, vehicle CAN telemetry, school zones, or touchscreen UI merely by launching the app. Those remain `UNKNOWN` until instrumented and hardware-validated. ADB commands do not run inside an APK; this is a Windows host deployment harness.

Same Android applicationId cannot run two independent versions at once. This is replacement-and-rollback, not literal blue/green. Old APK backup does not include private app data. `run-as` backup works only on debuggable installs; if unavailable the script stops by default. `adb install -r -d` downgrade is not guaranteed; script stops by default unless operator explicitly opts into that risk. Never `adb uninstall` or `pm clear` to force a downgrade.

## Commands (PowerShell)
1. Unzip to `D:\ASURE\MONTRIX_V27_REFACTORED` (one folder).
2. Baseline and backup, **no installation**:
   `powershell -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode baseline`
3. Inspect `D:\ASURE\MONTRIX_DEPLOY_RESULTS\report.json`, `blue_before\score.json`, backup files.
4. Candidate deployment (default refuses when backup/rollback cannot be guaranteed):
   `powershell -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode deploy`
5. **Explicit risk overrides only if you accept loss of data / failed rollback**:
   `powershell -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode deploy -AllowNoDataBackup -AllowUnsafeRollback`
6. Manual rollback after trial:
   `powershell -ExecutionPolicy Bypass -File .\MONTRIX_DEPLOY.ps1 -Mode rollback`

Do **not** run step 5 on the car before independently preserving the app data and proving rollback on a test device. On release-signed production apps, the debug candidate may fail signature matching; the script will stop. Do not uninstall the original app.

## Scoring
Per-test PASS/FAIL/WARN/UNKNOWN and weights saved as JSON. Critical failures block retention. Only shared PASS/FAIL checks count toward comparison. A candidate stays **only with a strictly positive improvement, zero newly failing tests, and zero critical failures**. This means an unchanged baseline normally leads to rollback, intentionally honoring the requested strict criterion. Missing QA is `UNKNOWN`, not success. No manufactured pass for OEM hardware.

## Coverage / limitations
- ADB connectivity, installed package, version, APK backup, optional run-as private data archive, disk, GPS permission, OEM package, launch, process, crash, ANR.
- Debug QA radio/music/seek/preset *dispatch* (not tuner proof); explicit unknown for RDS, trip recording, ignition, map, CAN, speed limits, factory popup, GPS and sleep/wake.
- Compile and static checks run before installation. Tests and logs are stored both before and after.
- Not yet implemented: exhaustive automated emulator integration tests, screenshot comparisons, station audio sensing, reliable app-data restoration, migration/downgrade safety proof, full ignition cycling and driving validation.

## Security and operational safety
The app is a driving aid, not a safety-certified instrument. Run while safely parked. Location history, logcat and backups can contain sensitive information; store the results locally, encrypt them, do not share unredacted. Never use `-AllowNoDataBackup` or `-AllowUnsafeRollback` casually.

## v27.1 safety repair (November 2026)
- `private_data.tar` now includes only directories actually present; binary stdout is validated with Python tarfile and all file payloads are read before declaring backup success. A failed archive is deleted.
- Backups of APK splits are checked as valid ZIP/APK archives, not merely nonempty files.
- Never clears logcat; uses a session marker for new-crash checks.
- ADB broadcast completion and `DISPATCHED` logging are **not** counted as passing hardware tests.
- Private-data backup is a hard deployment gate, even if the old override switch is passed.
- This still cannot guarantee downgrade compatibility, restoration of app-private data, or hardware correctness; automatic deployment remains fail-closed.
- `baseline` mode is safe to run on the car while parked; it does not install an APK.
