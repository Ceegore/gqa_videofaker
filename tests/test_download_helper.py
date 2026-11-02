import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from tools.get_presentmon import download_verified, main

class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.target=Path(self.t.name)/'nested'/'console.exe'
        self.data=b'SYNTHETIC DOWNLOAD FIXTURE, NOT A WINDOWS EXECUTABLE'
        self.lock={'sha256':hashlib.sha256(self.data).hexdigest(),'url':'https://example.invalid/test'}
    def test_exact_output_filename(self):
        opener=Mock(return_value=io.BytesIO(self.data))
        self.assertEqual(self.target,download_verified(self.lock,self.target,opener))
        self.assertTrue(self.target.is_file());self.assertEqual(self.data,self.target.read_bytes())
    def test_bad_digest_not_written(self):
        with self.assertRaises(ValueError):download_verified(self.lock,self.target,Mock(return_value=io.BytesIO(b'wrong')))
        self.assertFalse(self.target.exists())
    def test_existing_matching_file_no_network(self):
        self.target.parent.mkdir();self.target.write_bytes(self.data);opener=Mock()
        download_verified(self.lock,self.target,opener);opener.assert_not_called()
    def test_mismatched_existing_file_preserved(self):
        self.target.parent.mkdir();self.target.write_bytes(b'keep');opener=Mock()
        with self.assertRaises(ValueError):download_verified(self.lock,self.target,opener)
        self.assertEqual(b'keep',self.target.read_bytes());opener.assert_not_called()
    def test_directory_rejected(self):
        self.target.mkdir(parents=True)
        with self.assertRaises(ValueError):download_verified(self.lock,self.target,Mock())
    def test_oversized_response_rejected(self):
        with patch('tools.get_presentmon.LIMIT',4):
            with self.assertRaises(ValueError):download_verified(self.lock,self.target,Mock(return_value=io.BytesIO(self.data)))
        self.assertFalse(self.target.exists())
    def test_explicit_consent_required(self):
        with patch('sys.argv',['get_presentmon.py','--output',str(self.target)]), patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit) as e:main()
        self.assertEqual(2,e.exception.code)

if __name__=='__main__':unittest.main()
