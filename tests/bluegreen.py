#!/usr/bin/env python3
"""Montrix ADB blue/green orchestrator. Safe defaults: no deployment without rollback proof.

Uses only Python standard library, Android SDK adb, and a locally available Gradle.
Never uninstalls, clears app data, disables OEM tuner, or grants permissions.
"""
import argparse, datetime, hashlib, json, os, pathlib, re, shutil, subprocess, sys, time, zipfile, io, tarfile, uuid

# Windows PowerShell often uses cp1252; ADB output may contain undecodable bytes.
# Use safe ASCII-only console reporting, preserving full UTF-8 in files.
def console_safe(value):
 return str(value).encode('ascii', 'backslashreplace').decode('ascii')

PKG='com.monte.cwgradio' 
QA_ACTION=PKG+'.QA'
ACTIVITY='com.monte.montrix.DashboardActivity'
OLD_ACTIVITY='com.monte.cwgradio.DashboardActivity'
CRITICAL={'adb_online','package_installed','launch','process_alive','no_fatal','no_anr','oem_tuner_present','location_permission','storage_available'}
WEIGHTS={'adb_online':100,'package_installed':100,'launch':80,'process_alive':100,'no_fatal':100,'no_anr':100,'oem_tuner_present':60,'location_permission':40,'storage_available':40,'qa_receiver':20,'radio_dispatch':30,'music_dispatch':30,'seek_dispatch':30,'preset_dispatch':40,'rds_evidence':25,'trip_storage_evidence':30,'ignition_evidence':25,'gps_evidence':25,'map_evidence':15,'sleep_wake_evidence':25,'factory_popup_evidence':25,'speed_limit_evidence':15,'can_evidence':15}
class Runner:
 def __init__(self,args):
  self.a=args; self.base=pathlib.Path(__file__).resolve().parents[1]; self.out=pathlib.Path(args.output).resolve();self.out.mkdir(parents=True,exist_ok=True)
  self.adb=[args.adb]+(['-s',args.serial] if args.serial else [])
  self.report={'created':datetime.datetime.now().isoformat(),'package':PKG,'policy':'manual-hardware-acceptance','steps':[],'warnings':[]}
 def cmd(self,command,timeout=30,check=False):
  try:
   p=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=timeout)
   if check and p.returncode: raise RuntimeError((p.stdout+p.stderr)[-1600:])
   return p.returncode,p.stdout,p.stderr
  except subprocess.TimeoutExpired:return 124,'','TIMEOUT'
 def adbcall(self,*args,timeout=30):return self.cmd(self.adb+list(args),timeout)
 def shell(self,*args,timeout=30):return self.adbcall('shell',*args,timeout=timeout)
 def save(self,name,content): (self.out/name).write_text(content,encoding='utf-8',errors='replace')
 def record(self,name,ok,detail=''):
  self.report['steps'].append({'name':name,'ok':bool(ok),'detail':str(detail)[:3000]}); self.persist()
  if not ok:raise RuntimeError(name+': '+str(detail))
 def persist(self): (self.out/'report.json').write_text(json.dumps(self.report,indent=2,ensure_ascii=True),encoding='utf-8')
 def device(self):
  rc,stdout,stderr=self.adbcall('get-state');self.record('device_online',rc==0 and stdout.strip()=='device',stdout+stderr)
  rc,stdout,stderr=self.shell('getprop','ro.serialno');self.report['device_serial']=stdout.strip()
  rc,stdout,stderr=self.shell('getprop','ro.build.version.sdk');self.report['device_sdk']=stdout.strip()
  rc,stdout,stderr=self.shell('pm','path',PKG)
  self.record('package_exists',rc==0 and 'package:' in stdout,stdout+stderr)
  self.report['old_apk_paths']=[x.split('package:',1)[1].strip() for x in stdout.splitlines() if 'package:' in x]
  rc,stdout,stderr=self.shell('dumpsys','package',PKG,timeout=60)
  self.save('installed_package_before.txt',stdout+stderr)
  self.report['old_version']=re.search(r'versionCode=(\d+)',stdout).group(1) if re.search(r'versionCode=(\d+)',stdout) else None
  self.persist()
 def backup(self):
  """Preserve binary output exactly; validate archive and coverage before accepting it."""
  old=self.out/'backup';old.mkdir(exist_ok=True)
  # Do not overwrite the only known-good backup with a candidate during a repeat run.
  if (old/'installed_0.apk').exists():
   raise RuntimeError('Backup already exists: choose a fresh output directory for this trial; never overwrite the known-good APK')
  apk_paths=self.report['old_apk_paths']
  if not apk_paths: self.record('backup_apk_paths',False,'No installed APK paths')
  for n,path in enumerate(apk_paths):
   target=old/f'installed_{n}.apk'
   rc,data,err=self.adbcall('pull',path,str(target),timeout=180)
   valid=rc==0 and target.exists() and target.stat().st_size>10000
   if valid:
    try:
     with zipfile.ZipFile(target) as z: valid='AndroidManifest.xml' in z.namelist() and z.testzip() is None
    except (OSError,zipfile.BadZipFile):valid=False
   self.record(f'backup_apk_{n}',valid,err+'; ZIP integrity checked')
  # Inspect the actual directories. Missing directories are normal for new apps.
  rc,listing,err=self.adbcall('exec-out','run-as',PKG,'sh','-c','for p in files databases shared_prefs no_backup; do if test -d "$p"; then echo "$p"; fi; done',timeout=30)
  dirs=[x.strip() for x in listing.splitlines() if x.strip() in ('files','databases','shared_prefs','no_backup')]
  self.report['private_data_directories']=dirs
  if rc!=0:
   self.report['private_data_backup']='unavailable';self.report['warnings'].append('run-as unavailable: '+err.strip()[:250]);self.persist();return
  # Tar only extant directories. If all are absent, archive current dir so TAR remains valid.
  args=['exec-out','run-as',PKG,'tar','-cf','-','-C','.']+(dirs or ['.'])
  target=old/'private_data.tar'
  try:
   result=subprocess.run(self.adb+args,capture_output=True,timeout=180)
   if result.returncode!=0:raise RuntimeError('tar returned '+str(result.returncode)+': '+result.stderr.decode(errors='replace')[:500])
   # ADB exec-out sometimes produces a successful command with corrupt stdout.
   with tarfile.open(fileobj=io.BytesIO(result.stdout),mode='r:') as archive:
    members=archive.getmembers()
    if not members:raise RuntimeError('empty tar member list')
    if not all(d in {m.name.removeprefix('./').split('/')[0] for m in members} for d in dirs):
     raise RuntimeError('archive does not cover all private-data directories')
    for member in members:
     if member.isfile():
      stream=archive.extractfile(member)
      while stream and stream.read(1024*1024):pass
   target.write_bytes(result.stdout)
   self.report['private_data_backup']='validated'
   self.report['private_data_members']=len(members)
  except (Exception) as exc:
   target.unlink(missing_ok=True)
   self.report['private_data_backup']='invalid';self.report['warnings'].append('Private-data archive invalid: '+str(exc))
  for file in old.glob('*'):
   self.report.setdefault('backup_sha256',{})[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
  self.persist()

 def regression(self,label):
  directory=self.out/label;directory.mkdir(exist_ok=True)
  results=[]
  def add(name,status,detail=''):
   results.append({'name':name,'status':status,'weight':WEIGHTS.get(name,10),'critical':name in CRITICAL,'detail':detail[:800]})
  rc,stdout,stderr=self.adbcall('get-state');add('adb_online','PASS' if rc==0 and stdout.strip()=='device' else 'FAIL',stderr)
  rc,stdout,stderr=self.shell('pm','path',PKG);add('package_installed','PASS' if 'package:' in stdout else 'FAIL',stdout+stderr)
  rc,stdout,stderr=self.shell('dumpsys','package',PKG,timeout=60);(directory/'package.txt').write_text(stdout+stderr,encoding='utf-8',errors='replace')
  add('location_permission','PASS' if 'android.permission.ACCESS_FINE_LOCATION: granted=true' in stdout else 'WARN','GPS permission grant is required for route collection')
  rc,stdout,stderr=self.shell('df','/data');(directory/'storage.txt').write_text(stdout+stderr,encoding='utf-8',errors='replace')
  add('storage_available','PASS' if rc==0 and '100%' not in stdout else 'FAIL',stdout[-200:])
  rc,stdout,stderr=self.shell('pm','path','com.syu.radio');add('oem_tuner_present','PASS' if 'package:' in stdout else 'WARN','OEM package may be com.syu.carradio')
  if not 'package:' in stdout:
   rc,stdout,stderr=self.shell('pm','path','com.syu.carradio');results[-1]['status']='PASS' if 'package:' in stdout else 'WARN'
  # Capture a marker instead of clearing system logs; preserve preexisting crash evidence.
  marker='MONTRIX_RUN_'+uuid.uuid4().hex[:12]
  self.shell('log','-t','MONTRIX_HARNESS',marker)
  (directory/'marker.txt').write_text(marker,encoding='utf-8')
  rc,stdout,stderr=self.shell('monkey','-p',PKG,'-c','android.intent.category.LAUNCHER','1',timeout=30)
  add('launch','PASS' if rc==0 and ('Events injected: 1' in stdout or 'Events injected: 1' in stderr) else 'FAIL',stdout+stderr)
  time.sleep(4)
  rc,stdout,stderr=self.shell('pidof',PKG);add('process_alive','PASS' if stdout.strip() else 'FAIL',stdout+stderr)
  rc,logs,stderr=self.adbcall('logcat','-d','-v','threadtime',timeout=60)
  (directory/'logcat.txt').write_text(logs+stderr,encoding='utf-8',errors='replace')
  session_logs=logs.split(marker,1)[-1] if marker in logs else ''
  add('no_fatal',('UNKNOWN' if not session_logs else ('FAIL' if re.search(r'FATAL EXCEPTION|Fatal signal \d+',session_logs,re.I) and PKG in session_logs else 'PASS')),'Only post-marker logs evaluated; no marker means UNKNOWN')
  add('no_anr',('UNKNOWN' if not session_logs else ('FAIL' if re.search(r'ANR in '+re.escape(PKG),session_logs) else 'PASS')))
  # Read-only QA snapshot: never toggle radio/music during regression.
  rc,stdout,stderr=self.shell('am','broadcast','-a',QA_ACTION,'-n',PKG+'/com.monte.montrix.QaReceiver','--es','op','snapshot')
  qa_ok=rc==0 and 'Broadcast completed' in stdout
  time.sleep(1)
  rc2,log,err=self.adbcall('logcat','-d','-s','MONTRIX_QA:I','*:S')
  (directory/'qa_snapshot.txt').write_text(stdout+stderr+log+err,encoding='utf-8',errors='replace')
  snapshot_lines=[line for line in log.splitlines() if 'SNAPSHOT ' in line]
  add('qa_receiver','PASS' if snapshot_lines else ('WARN' if qa_ok else 'UNKNOWN'),
      ('Read-only snapshot emitted: '+snapshot_lines[-1]) if snapshot_lines else 'No receiver acknowledgment')
  for name in ['radio_dispatch','music_dispatch','seek_dispatch','preset_dispatch']:
   add(name,'UNKNOWN','No intrusive commands sent. Hardware response requires parked manual test.')
  for name in ['rds_evidence','trip_storage_evidence','ignition_evidence','gps_evidence','map_evidence','sleep_wake_evidence','factory_popup_evidence','speed_limit_evidence','can_evidence']:
   add(name,'UNKNOWN','Cannot prove hardware behavior from passive ADB snapshot; dedicated instrumentation or real driving test needed')
  # Only comparable known results score; UNKNOWN is never treated as PASS.
  known=[x for x in results if x['status'] in ('PASS','FAIL')]
  penalty=sum(x['weight'] for x in known if x['status']=='FAIL')
  warnings=sum(x['weight'] for x in results if x['status']=='WARN')
  unknown=sum(x['weight'] for x in results if x['status']=='UNKNOWN')
  score={'failure_penalty':penalty,'warning_weight':warnings,'unknown_weight':unknown,'known_weight':sum(x['weight'] for x in known),'critical_failures':[x['name'] for x in results if x['critical'] and x['status']=='FAIL'],'results':results}
  (directory/'score.json').write_text(json.dumps(score,indent=2,ensure_ascii=True),encoding='utf-8')
  self.report[label]=score;self.persist();return score
 def build(self):
  rc,stdout,stderr=self.cmd([sys.executable,str(self.base/'tests/check_source.py')]);self.record('structural_tests',rc==0,stdout+stderr)
  gradle=self.a.gradle or shutil.which('gradle')
  self.record('gradle_found',bool(gradle),'Set --gradle to gradle.bat path')
  rc,stdout,stderr=self.cmd([gradle,'--no-daemon','clean',':app:assembleDebug'],timeout=900)
  self.save('gradle_build.txt',stdout+stderr);self.record('gradle_build',rc==0,(stdout+stderr)[-1400:])
  apk=self.base/'app/build/outputs/apk/debug/app-debug.apk'
  self.record('candidate_apk',apk.exists() and apk.stat().st_size>10000,str(apk))
  shutil.copy2(apk,self.out/'candidate.apk')
  self.report['candidate_sha256']=hashlib.sha256(apk.read_bytes()).hexdigest();self.persist()
  return apk
 def rollback(self):
  backup=self.out/'backup/installed_0.apk'
  self.record('rollback_apk_available',backup.exists(),str(backup))
  # adb install -r -d might be disallowed by OS for downgrades. Never uninstall to force it.
  rc,stdout,stderr=self.adbcall('install','-r','-d',str(backup),timeout=180)
  self.record('rollback_install',rc==0 and 'Success' in stdout,stdout+stderr)
  rc,version,err=self.shell('dumpsys','package',PKG,timeout=60)
  expected=self.report.get('old_version')
  actual=re.search(r'versionCode=(\d+)',version)
  self.record('rollback_version_verified',bool(actual and expected and actual.group(1)==str(expected)),f'expected={expected}, actual={actual.group(1) if actual else None}')
  self.report['rollback_status']='APK version verified; private data compatibility UNVERIFIED'
  self.persist()
 def execute(self):
  self.device();self.backup();baseline=self.regression('blue_before')
  apk=self.build()
  # Version must be strictly higher; downgrade may fail even if APK backup exists.
  if self.report.get('private_data_backup')!='validated':
   self.record('data_backup_gate',False,'Private data backup invalid or unavailable. Deployment prohibited.')
  if not self.a.trial_consent:
   self.record('trial_consent_gate',False,'Trial installation requires -TrialConsent; current hardware behavior is not fully observable via ADB.')
  if not self.a.allow_unsafe_rollback:
   self.record('rollback_gate',False,'Android may reject downgrading APK version; cannot guarantee rollback without root or a version-compatible rollback APK.')
  self.record('baseline_critical_gate',not baseline['critical_failures'],baseline['critical_failures'])
  unknown_critical=[x['name'] for x in baseline['results'] if x['critical'] and x['status'] not in ('PASS','FAIL')]
  if unknown_critical:self.record('baseline_unknown_gate',False,'Critical checks unverified: '+', '.join(unknown_critical))
  backup=self.out/'backup/installed_0.apk'
  archive=self.out/'backup/private_data.tar'
  self.record('backup_files_still_present',backup.exists() and archive.exists(),str(backup)+' '+str(archive))
  with tarfile.open(archive,'r:') as tar:
   self.record('backup_archive_revalidated',len(tar.getmembers())>0,'Archive readable immediately before install')
  rc,stdout,stderr=self.adbcall('install','-r',str(apk),timeout=180)
  self.record('candidate_install',rc==0 and 'Success' in stdout,stdout+stderr)
  green=self.regression('green_after')
  # No hardware check may be considered an improvement merely because it changed from UNKNOWN to PASS.
  self.report['hardware_unknown_after']=[x['name'] for x in green['results'] if x['status']=='UNKNOWN']
  self.persist()
  before={x['name']:x for x in baseline['results']}
  after={x['name']:x for x in green['results']}
  regressions=[name for name,x in after.items() if x['status']=='FAIL' and before[name]['status']!='FAIL']
  comparable=[name for name,x in after.items() if x['status'] in ('PASS','FAIL') and before[name]['status'] in ('PASS','FAIL')]
  improvement=sum(WEIGHTS.get(n,10)*(int(before[n]['status']=='FAIL')-int(after[n]['status']=='FAIL')) for n in comparable)
  # The harness cannot observe audio at the speaker, actual GPS speed or OEM CAN.
  # A non-regression is not evidence of improvement, and cannot auto-accept a candidate.
  new_critical=[name for name,x in after.items() if x['critical'] and x['status']=='FAIL']
  new_warnings=[name for name,x in after.items() if x['status']=='WARN' and before[name]['status']=='PASS']
  safe_to_trial=not regressions and not new_critical and not new_warnings
  self.report['decision']={'keep':None,'status':'AWAITING_MANUAL_HARDWARE_ACCEPTANCE' if safe_to_trial else 'REJECTED_ROLLBACK_REQUIRED',
   'improvement':improvement,'regressions':regressions,'new_critical':new_critical,'new_warnings':new_warnings,
   'comparable_checks':len(comparable),'hardware_verified':False}
  self.persist()
  if not safe_to_trial:
   try:
    self.rollback()
   except Exception as rollback_error:
    self.report['decision']['status']='ROLLBACK_FAILED_MANUAL_RECOVERY_REQUIRED'
    self.report['decision']['rollback_error']=str(rollback_error)
    self.persist()
    raise RuntimeError('Critical regression and rollback FAILED. Do not uninstall or clear data: '+str(rollback_error))
   self.report['decision']['status']='REJECTED_APK_ROLLBACK_VERIFIED_DATA_UNVERIFIED';self.persist()
   raise RuntimeError('Critical regression; old APK version restored. Private data compatibility unverified.')
  self.report['warnings'].append('Candidate remains installed for PARKED manual hardware testing. Not accepted; rollback is available but data restoration is not guaranteed.')
  self.persist()
  print('TRIAL HOLD: Candidate installed; no critical automated regression detected. NOT ACCEPTED. Perform parked manual checks or use rollback mode.')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('mode',choices=['deploy','baseline','rollback'])
 parser.add_argument('--adb',default='adb');parser.add_argument('--serial');parser.add_argument('--gradle');parser.add_argument('--output',default='montrix_deploy_results')
 parser.add_argument('--allow-no-data-backup',action='store_true',help='DANGEROUS: permit deployment without private app data backup')
 parser.add_argument('--allow-unsafe-rollback',action='store_true',help='DANGEROUS: permit replacement without verified downgrade rollback')
 parser.add_argument('--trial-consent',action='store_true',help='Explicit permission to install a trial candidate despite non-verifiable hardware checks')
 args=parser.parse_args();run=Runner(args)
 try:
  if args.mode=='deploy':run.execute()
  elif args.mode=='baseline':run.device();run.backup();run.regression('blue_before')
  else:run.rollback()
 except Exception as error:
  run.report['error']=str(error);run.persist();print('STOP:',console_safe(error),file=sys.stderr);return 2
 print('Report:',console_safe(run.out/'report.json'));return 0
if __name__=='__main__':sys.exit(main())
