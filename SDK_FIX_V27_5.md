# Montrix v27.5 SDK discovery patch

The v27.4 trial failed during Gradle build because `local.properties` did not identify the Android SDK. No APK was installed.

v27.5 checks `-SdkPath`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, existing local.properties, and standard Windows SDK directories. It verifies `platforms/android-35/android.jar` and build-tools, then writes `local.properties` in Gradle-safe syntax. It refuses deployment if the SDK cannot be validated. The required `& $Adb connect $device` remains unchanged.

Example:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\ASURE\MONTRIX_V27_REFACTORED\MONTRIX_DEPLOY.ps1" -Mode deploy -device '192.168.1.159:5555' -SdkPath "$env:LOCALAPPDATA\Android\Sdk" -Results 'D:\ASURE\MONTRIX_TRIAL_DEPLOY_01' -TrialConsent -AllowUnsafeRollback
```

**Warning:** `-AllowUnsafeRollback` is an explicit acceptance of risk; downgrading may be blocked and data may not be restorable. This is not a hardware-verified release. Review report after run.
