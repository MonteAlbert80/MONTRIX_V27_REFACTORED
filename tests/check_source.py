"""Static safety gates; not a substitute for Android compilation or physical-device testing."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
java=root/"app/src/main/java/com/monte/montrix"
assert java.is_dir()
files=list(java.rglob("*.java"))
assert len(files)>=20
for p in files:
    s=p.read_text()
    assert re.search(r"package com.monte.montrix(?:.[a-z]+)?;",s),p
    assert "package com.monte.cwgradio" not in s,p
    assert "import com.monte.cwgradio" not in s,p
    assert "class RadioState" not in s,p
assert "com.monte.cwgradio" in (root/"app/build.gradle").read_text(), "Must preserve Android application ID"
assert "namespace 'com.monte.montrix'" in (root/"app/build.gradle").read_text()
manifest=(root/"app/src/main/AndroidManifest.xml").read_text()
for cls in ["DashboardActivity","MainActivity","RadioActivity","MusicActivity","ToggleActivity","NativeRadioService","BootReceiver"]:
    assert 'android:name="com.monte.montrix.'+cls+'"' in manifest,cls
dashboard=(java/"DashboardActivity.java").read_text()
assert "RadioTextPresenter.show(source,title,detail,f,r,p)" in dashboard
assert "tripRecorder.record(l)" in dashboard
assert "isRealFyt() && tripRecorder!=null" in dashboard
assert (java/"NativeRadioService.java").is_file()
assert (java/"SyuRadioClient.java").is_file()
assert (java/"NativeRdsReader.java").is_file()
assert (java/"OfflineTexasMapView.java").is_file()
print("PASS: Java namespace, compatibility ID, component manifest, radio/map/trips integrations")
