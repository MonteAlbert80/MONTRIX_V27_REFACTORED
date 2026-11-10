# v27.2 Windows console-encoding fix

## Cause
ADB logcat can contain undecodable byte sequences. Python replaces them with U+FFFD, which cannot be printed by cp1252 and some other Windows console encodings.

## Fix
- PowerShell temporarily enables UTF-8 Python IO and restores the environment afterward.
- Python console messages escape non-ASCII characters, so they remain printable even if the terminal is cp1252.
- All report, score and log files use explicit UTF-8 output; JSON reports escape non-ASCII by default.
- The fix does not change the APK, car firmware, tuner, or Android application code.

## Command
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\ASURE\MONTRIX_V27_REFACTORED\MONTRIX_DEPLOY.ps1" -Mode baseline`

If the report still stops, attach `D:\ASURE\MONTRIX_DEPLOY_RESULTS\report.json` and the newest `blue_before/logcat.txt`. No deployment occurs in baseline mode.
