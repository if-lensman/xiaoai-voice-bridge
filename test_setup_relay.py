"""Exercise first-install configuration without any network or real credentials."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        shutil.copy2(Path(__file__).with_name('setup_relay.py'),self.root/'setup_relay.py')
    def run_setup(self,text):
        return subprocess.run([sys.executable,'setup_relay.py'],cwd=self.root,input=text,text=True,capture_output=True)
    def test_interactive_private_config_and_no_secret_output(self):
        key='test-only-not-a-cloud-credential'
        result=self.run_setup('192.168.1.100\n192.168.1.101\n'+key+'\n')
        self.assertEqual(result.returncode,0,result.stderr)
        config=json.loads((self.root/'private/service-config.json').read_text())
        self.assertEqual(config['host'],'192.168.1.100');self.assertEqual(config['seconds'],0)
        self.assertEqual(len(config['token']),64)
        self.assertNotIn(key,result.stdout+result.stderr)
        self.assertNotIn(config['token'],result.stdout+result.stderr)
        self.assertEqual((self.root/'private/volc-api-key').stat().st_mode & 0o777,0o600)
        before=(self.root/'private/service-config.json').read_bytes()
        self.assertNotEqual(self.run_setup('').returncode,0)
        self.assertEqual((self.root/'private/service-config.json').read_bytes(),before)
    def test_public_address_rejected_before_key(self):
        self.assertNotEqual(self.run_setup('8.8.8.8\n').returncode,0)
        self.assertFalse((self.root/'private/volc-api-key').exists())
    def test_malformed_key_leaves_no_configuration(self):
        self.assertNotEqual(self.run_setup('192.168.1.100\n192.168.1.101\ninvalid key\n').returncode,0)
        self.assertFalse((self.root/'private/service-config.json').exists())

if __name__=='__main__':unittest.main()
