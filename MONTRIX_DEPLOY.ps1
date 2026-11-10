param(
 [ValidateSet('baseline','deploy','rollback')][string]$Mode='baseline',
 [string]$Adb='D:\platform-tools-latest-windows\platform-tools\adb.exe',
 [string]$Gradle='D:\platform-tools-latest-windows\gradle-8.9\bin\gradle.bat',
 [string]$device='192.168.1.159:5555',
 [string]$SdkPath='',
 [string]$Serial='',
 [string]$Results='D:\ASURE\MONTRIX_DEPLOY_RESULTS',
 [switch]$AllowNoDataBackup,
 [switch]$TrialConsent,
 [switch]$AllowUnsafeRollback
)
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path $Adb)) { $found=Get-Command adb -ErrorAction SilentlyContinue; if($found){$Adb=$found.Source}else{throw "ADB not found: $Adb"} }
# Always establish the TCP/IP ADB connection before the regression runner.
# -device is configurable; -Serial remains an optional backward-compatible alias.
if ($Serial) { $device = $Serial }
if ([string]::IsNullOrWhiteSpace($device)) { throw 'Device address cannot be empty.' }
Write-Host "Connecting ADB to $device ..."
& $Adb connect $device
$connectExit = $LASTEXITCODE
if ($connectExit -ne 0) { throw "ADB connect failed for $device (exit $connectExit)." }
$connectedDevices = & $Adb devices
if ($LASTEXITCODE -ne 0 -or -not ($connectedDevices | Where-Object { $_ -match ('^' + [regex]::Escape($device) + '\s+device\s*$') })) {
 throw "ADB device $device is not online after connect. Check Wi-Fi, ADB authorization and IP address."
}
# Discover the Android SDK only when building a candidate. Never guess an invalid path.
if ($Mode -eq 'deploy') {
 $sdkCandidates = @()
 if ($SdkPath) { $sdkCandidates += $SdkPath }
 if ($env:ANDROID_HOME) { $sdkCandidates += $env:ANDROID_HOME }
 if ($env:ANDROID_SDK_ROOT) { $sdkCandidates += $env:ANDROID_SDK_ROOT }
 $props = Join-Path $Root 'local.properties'
 if (Test-Path $props) {
   $sdkLine = Get-Content $props | Where-Object { $_ -match '^\s*sdk\.dir\s*=' } | Select-Object -First 1
   if ($sdkLine) { $sdkCandidates += (($sdkLine -split '=',2)[1].Trim() -replace '\\:',':' -replace '\\\\','\') }
 }
 $sdkCandidates += @(
   (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
   (Join-Path $env:USERPROFILE 'AppData\Local\Android\Sdk'),
   'C:\Android\Sdk',
   'D:\Android\Sdk',
   'D:\Android\android-sdk',
   'D:\platform-tools-latest-windows\Android\Sdk'
 )
 $sdk = $null
 foreach ($candidate in $sdkCandidates) {
   if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
   $candidate = [Environment]::ExpandEnvironmentVariables($candidate.Trim('"'))
   if ((Test-Path (Join-Path $candidate 'platforms')) -and (Test-Path (Join-Path $candidate 'build-tools'))) {
     $sdk = (Resolve-Path $candidate).Path
     break
   }
 }
 if (-not $sdk) {
   throw "Android SDK not found. Install Android SDK Platform 35 and Build Tools, or rerun with -SdkPath 'C:\Users\YOUR_USER\AppData\Local\Android\Sdk'. No APK installed."
 }
 if (-not (Test-Path (Join-Path $sdk 'platforms\android-35\android.jar'))) {
   throw "SDK found at $sdk but Android API 35 is missing. Install SDK Platform 35 first. No APK installed."
 }
 $env:ANDROID_HOME = $sdk
 $env:ANDROID_SDK_ROOT = $sdk
 # Android local.properties uses forward slashes even on Windows.
 $sdkGradle = $sdk.Replace('\','/')
 [System.IO.File]::WriteAllText($props, "sdk.dir=$sdkGradle`n", [System.Text.UTF8Encoding]::new($false))
 Write-Host "Android SDK ready: $sdk"
}
$cmd=@((Join-Path $Root 'tests\bluegreen.py'),$Mode,'--adb',$Adb,'--output',$Results,'--serial',$device)
if($Mode -eq 'deploy'){$cmd+=@('--gradle',$Gradle)}
if($AllowNoDataBackup){$cmd+='--allow-no-data-backup'}
if($AllowUnsafeRollback){$cmd+='--allow-unsafe-rollback'}
if($TrialConsent){$cmd+='--trial-consent'}
# Python console output must be safe regardless of Windows' active code page.
$oldPythonIoEncoding=$env:PYTHONIOENCODING
$oldPythonUtf8=$env:PYTHONUTF8
try {
 $env:PYTHONIOENCODING='utf-8:backslashreplace'
 $env:PYTHONUTF8='1'
 & python @cmd
 $pythonExitCode=$LASTEXITCODE
} finally {
 $env:PYTHONIOENCODING=$oldPythonIoEncoding
 $env:PYTHONUTF8=$oldPythonUtf8
}

if($pythonExitCode -ne 0){throw "Montrix deployment STOPPED. Review $Results\report.json"}
