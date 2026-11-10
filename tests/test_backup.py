"""Offline tests for the repaired backup validation; no device required."""
import io, tarfile, unittest, pathlib, tempfile, argparse, importlib.util, zipfile, subprocess
spec=importlib.util.spec_from_file_location('bluegreen',pathlib.Path(__file__).with_name('bluegreen.py'))
bg=importlib.util.module_from_spec(spec);spec.loader.exec_module(bg)
class BackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  args=argparse.Namespace(adb='adb',serial=None,output=self.tmp.name,gradle=None,allow_no_data_backup=False,allow_unsafe_rollback=False)
  self.runner=bg.Runner(args)
  self.runner.report['old_apk_paths']=['/data/app/base.apk']
  self.apk=pathlib.Path(self.tmp.name)/'fixture.apk'
  with zipfile.ZipFile(self.apk,'w') as z:z.writestr('AndroidManifest.xml','manifest');z.writestr('classes.dex',b'0'*20000)
 def tearDown(self):self.tmp.cleanup()
 def test_valid_tar(self):
  tar=io.BytesIO()
  with tarfile.open(fileobj=tar,mode='w') as t:
   for name in ('files','databases'):
    data=b'example'; info=tarfile.TarInfo(name+'/example');info.size=len(data);t.addfile(info,io.BytesIO(data))
  self.run_case(tar.getvalue(),['files','databases'],'validated')
 def test_corrupted_tar(self):
  self.run_case(b'tar: files: No such file or directory\n'+b'X'*2048,['files'],'invalid')
 def test_missing_directory(self):
  tar=io.BytesIO()
  with tarfile.open(fileobj=tar,mode='w') as t:
   data=b'x';info=tarfile.TarInfo('files/data');info.size=1;t.addfile(info,io.BytesIO(data))
  self.run_case(tar.getvalue(),['files','databases'],'invalid')
 def run_case(self,blob,dirs,expected):
  r=self.runner
  def fake_adb(*args,**kw):
   if args[0]=='pull':
    pathlib.Path(args[2]).write_bytes(self.apk.read_bytes());return 0,'',''
   if args[0]=='exec-out':return 0,'\n'.join(dirs)+'\n',''
   raise AssertionError(args)
  r.adbcall=fake_adb
  original=bg.subprocess.run
  def fake_run(*args,**kw):return subprocess.CompletedProcess(args[0],0,blob,b'')
  bg.subprocess.run=fake_run
  try:r.backup()
  finally:bg.subprocess.run=original
  self.assertEqual(r.report['private_data_backup'],expected)
  self.assertEqual((pathlib.Path(self.tmp.name)/'backup/private_data.tar').exists(),expected=='validated')
if __name__=='__main__':unittest.main()
