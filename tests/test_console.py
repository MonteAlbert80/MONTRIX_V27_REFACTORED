import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bluegreen import console_safe, Runner
from argparse import Namespace
from tempfile import TemporaryDirectory
class ConsoleTests(unittest.TestCase):
 def test_invalid_unicode_is_ascii_safe(self):
  self.assertEqual(console_safe('x\ufffd\udcff'), 'x\\ufffd\\udcff')
  console_safe('x\ufffd').encode('cp1252')
 def test_report_unicode_is_safe(self):
  with TemporaryDirectory() as td:
   r=Runner(Namespace(adb='adb',serial=None,output=td))
   r.report['error']='bad \ufffd text'
   r.persist()
   self.assertIn('\\ufffd',Path(td,'report.json').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
