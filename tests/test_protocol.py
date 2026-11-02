import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from tools.package_release import pack, verify_zip, validate_pe
from tools.verify_presentmon import PM_SHA256, PM_VERSION, KNOWN_EVENTS, classify

ROOT=Path(__file__).resolve().parents[1]

class ProtocolTests(unittest.TestCase):
    def test_pinned_observer_consistent(self):
        lock=json.loads((ROOT/'tools/presentmon.lock.json').read_text())
        self.assertEqual(PM_SHA256,lock['sha256']);self.assertEqual(PM_VERSION,lock['version'])
    def test_actual_cpp_event_names_known(self):
        import re
        names=set(re.findall(r'log\.event\("([A-Z_]+)"',(ROOT/'src/main.cpp').read_text()))
        self.assertTrue(names);self.assertEqual(set(),names-KNOWN_EVENTS)
    def test_no_shader_runtime_dependency(self):
        source='\n'.join(p.read_text() for p in (ROOT/'src').glob('*.cpp'))
        self.assertNotIn('D3DCompile(',source)
        self.assertIn('fxc.exe',(ROOT/'CMakeLists.txt').read_text())
    def test_shader_work_bounded(self):
        text=(ROOT/'src/shaders.hlsl').read_text()
        self.assertIn('i<32',text);self.assertIn('i >= iterations',text)
    def test_no_live_verified_hud(self):
        text=(ROOT/'src/scene.cpp').read_text()
        self.assertIn('NOT YET INDEPENDENTLY VERIFIED',text)
        self.assertNotIn('FSE_VERIFIED',text)
    def test_reject_fake_executable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.exe';p.write_bytes(b'not a Windows program')
            with self.assertRaises(ValueError):validate_pe(p)
    def test_zip_manifest_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'stage';root.mkdir();(root/'a.txt').write_text('sample')
            output=Path(d)/'test.zip'
            self.assertEqual(2,pack(root,output));self.assertEqual(2,verify_zip(output))
    def test_zip_tamper_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('a.txt','changed');z.writestr('SHA256SUMS.json',json.dumps({'a.txt':'0'*64}))
            with self.assertRaises(ValueError):verify_zip(p)
    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('../x','bad');z.writestr('SHA256SUMS.json','{}')
            with self.assertRaises(ValueError):verify_zip(p)
    def test_zip_case_collision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('A','x');z.writestr('a','x');z.writestr('SHA256SUMS.json','{}')
            with self.assertRaises(ValueError):verify_zip(p)
    def test_zip_cannot_package_into_itself(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError):pack(root,root/'bad.zip')
    def test_fixture_expectations(self):
        for p in sorted((ROOT/'tests/fixtures').glob('*/expected.json')):
            with self.subTest(case=p.parent.name):
                expected=json.loads(p.read_text());actual=classify(p.parent)
                for key,value in expected.items():self.assertEqual(value,actual[key])
    def test_optional_manifests_not_live_evidence(self):
        status=json.loads((ROOT/'KIT_STATUS.json').read_text())
        self.assertRegex(status['windows_msvc_build'],r'^EXECUTED_PASS_CI_[0-9]+$')
        self.assertIn(status['hardware_fse_validation'],{'NOT_EXECUTED','NOT_VERIFIED'})
        self.assertIsInstance(status.get('current_ci_run'),int)

if __name__=='__main__':unittest.main()
