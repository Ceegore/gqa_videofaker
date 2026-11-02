import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.verify_presentmon import classify, exit_code, write_report
from tests.fixture_factory import make, refresh, mutate_csv, mutate_events, write_json, BASE, FREQ

class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=make(Path(self.tmp.name)/'run')
    def check(self,reason=None,verdict=None):
        report=classify(self.p)
        if reason is not None:self.assertEqual(reason,report['reason'],report)
        if verdict is not None:self.assertEqual(verdict,report['verdict'],report)
        return report
    def session(self, **fields):
        s=json.loads((self.p/'session.json').read_text());s.update(fields);write_json(self.p/'session.json',s)
    def test_boolean_observer_exit_rejected(self):
        self.session(observer_exit_code=False);self.check('UNVERIFIED_OBSERVER_EXIT')
    def test_boolean_app_exit_rejected(self):
        self.session(app_exit_code=False);self.check('UNVERIFIED_EXIT_MISMATCH')
    def test_boolean_schema_rejected(self):
        self.session(schema=True);self.check('UNVERIFIED_SESSION_SCHEMA')
    def test_zero_displayed_duration_does_not_count(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(DisplayedTime='0') for r in rows]);self.check('UNVERIFIED_INSUFFICIENT_DISPLAYED_FRAMES')
    def test_runner_error_rejected(self):
        self.session(runner_error='observer handoff failed');self.check('UNVERIFIED_RUNNER_ERROR')
    def test_invalid_hash_type_does_not_crash(self):
        self.session(observer_sha256=123);self.check('UNVERIFIED_INPUT')
    def test_legacy_flip(self):
        r=self.check('CLASSIC_EXCLUSIVE_OBSERVED','SYNTHETIC_PASS')
        self.assertEqual('SYNTHETIC_LEGACY_MATCH',r['presentation_proof'])
        self.assertEqual('NOT_EVALUATED',r['recorder_result'])
        self.assertEqual('SYNTHETIC_NOT_HARDWARE',r['hardware_fse_validation'])
    def test_legacy_copy(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Hardware: Legacy Copy to front buffer') for r in rows]);self.check(verdict='SYNTHETIC_PASS')
    def test_cpUBusy_header_alias(self):
        path=self.p/'presentmon.csv'
        lines=path.read_text(encoding='utf-8').splitlines()
        lines[0]=lines[0].replace('MsCPUBusy','CPUBusy')
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        refresh(self.p)
        self.check('CLASSIC_EXCLUSIVE_OBSERVED','SYNTHETIC_PASS')
    def test_missing_busy_column_rejected(self):
        path=self.p/'presentmon.csv'
        lines=path.read_text(encoding='utf-8').splitlines()
        lines[0]=lines[0].replace('MsCPUBusy','UnknownBusy')
        path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        refresh(self.p)
        self.check('UNVERIFIED_SCHEMA')
    def test_independent(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Hardware: Independent Flip') for r in rows]);self.check('FAIL_NOT_CLASSIC_EXCLUSIVE','FAIL')
    def test_hardware_composed(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Hardware Composed: Independent Flip') for r in rows]);self.check('FAIL_NOT_CLASSIC_EXCLUSIVE')
    def test_composed(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Composed: Flip') for r in rows]);self.check('FAIL_NOT_CLASSIC_EXCLUSIVE')
    def test_one_bad_frame(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(PresentMode='Composed: Flip'));self.check('FAIL_PRESENT_MODE_CHANGED')
    def test_guard_catches_transition(self):
        mutate_csv(self.p,lambda rows,fields:rows[170].update(PresentMode='Composed: Flip'));self.check('FAIL_PRESENT_MODE_CHANGED')
    def test_warmup_not_capture(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Composed: Flip') for r in rows[180:500]]);self.check('FAIL_PRESENT_MODE_CHANGED')
    def test_warmup_can_be_different(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(PresentMode='Composed: Flip') for r in rows[:40]]);self.check(verdict='SYNTHETIC_PASS')
    def test_unknown_mode(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(PresentMode='Unknown'));self.check('UNVERIFIED_UNKNOWN_PRESENT_MODE')
    def test_missing_frame(self):
        mutate_csv(self.p,lambda rows,fields:rows.pop(300));self.check('UNVERIFIED_FRAME_GAP')
    def test_duplicate_frame(self):
        mutate_csv(self.p,lambda rows,fields:rows.insert(300,dict(rows[300])));self.check('UNVERIFIED_DUPLICATE_PRESENT')
    def test_wrong_pid(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(ProcessID='123') for r in rows]);self.check('UNVERIFIED_NO_TARGET_FRAMES')
    def test_other_pid_ignored(self):
        mutate_csv(self.p,lambda rows,fields:rows.append(dict(rows[300],ProcessID='123',PresentMode='Composed: Flip')));self.check(verdict='SYNTHETIC_PASS')
    def test_multiple_swapchains(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(SwapChainAddress='0x567800'));self.check('UNVERIFIED_AMBIGUOUS_SWAPCHAIN')
    def test_zero_swapchain(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(SwapChainAddress='0'));self.check('UNVERIFIED_SWAPCHAIN')
    def test_wrong_application(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(Application='Other.exe'));self.check('UNVERIFIED_APPLICATION_NAME')
    def test_runtime_d3d9(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(PresentRuntime='D3D9'));self.check('UNVERIFIED_RUNTIME')
    def test_missing_qpc(self):
        def remove(rows,fields):
            fields.remove('CPUStartQPC')
            for r in rows:del r['CPUStartQPC']
        mutate_csv(self.p,remove);self.check('UNVERIFIED_TIME_AXIS')
    def test_ms_not_ticks(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(CPUStartQPC=str(int(r['CPUStartQPC'])//10000)) for r in rows]);self.check('UNVERIFIED_NO_TARGET_FRAMES')
    def test_fractional_qpc_refused(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(CPUStartQPC='1.2'));self.check('UNVERIFIED_INTEGER')
    def test_qpc_overflow(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(CPUStartQPC=str(1<<64)));self.check('UNVERIFIED_INTEGER_RANGE')
    def test_time_reconciliation(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(MsCPUBusy='9'));self.check('UNVERIFIED_TIME_RECONCILIATION')
    def test_nan(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(MsCPUBusy='NaN'));self.check('UNVERIFIED_NUMBER')
    def test_negative_busy(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(MsCPUBusy='-1'));self.check('UNVERIFIED_NUMBER')
    def test_long_cpu_frame(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(MsCPUBusy='300'));self.check('UNVERIFIED_LONG_CPU_FRAME')
    def test_no_displayed_frames(self):
        mutate_csv(self.p,lambda rows,fields:[r.update(DisplayedTime='NA') for r in rows]);self.check('UNVERIFIED_INSUFFICIENT_DISPLAYED_FRAMES')
    def test_reordered_columns(self):
        mutate_csv(self.p,lambda rows,fields:fields.reverse());self.check(verdict='SYNTHETIC_PASS')
    def test_bom(self):
        f=self.p/'presentmon.csv';f.write_bytes(b'\xef\xbb\xbf'+f.read_bytes());refresh(self.p);self.check(verdict='SYNTHETIC_PASS')
    def test_extra_column(self):
        def add(rows,fields):
            fields.append('NewMetric')
            for r in rows:r['NewMetric']='x,y'
        mutate_csv(self.p,add);self.check(verdict='SYNTHETIC_PASS')
    def test_truncated_csv(self):
        with (self.p/'presentmon.csv').open('a') as f:f.write('FSEProbe.exe,4242\n')
        refresh(self.p);self.check('UNVERIFIED_CSV_ROW')
    def test_empty_csv(self):
        (self.p/'presentmon.csv').write_text('');refresh(self.p);self.check('UNVERIFIED_CSV_SIZE')
    def test_duplicate_header(self):
        p=self.p/'presentmon.csv';p.write_text(p.read_text().replace('Application,ProcessID','ProcessID,ProcessID',1));refresh(self.p);self.check('UNVERIFIED_DUPLICATE_HEADER')
    def test_no_capture_frames(self):
        mutate_csv(self.p,lambda rows,fields:rows.__delitem__(slice(100,None)));self.check('UNVERIFIED_NO_INTERVAL_FRAMES')
    def test_hash_mismatch(self):
        with (self.p/'presentmon.csv').open('a') as f:f.write('\n')
        self.check('UNVERIFIED_EVIDENCE_HASH')
    def test_observer_exit(self):
        self.session(observer_exit_code=1);self.check('UNVERIFIED_OBSERVER_EXIT')
    def test_observer_timeout(self):
        self.session(observer_timeout=True);self.check('UNVERIFIED_OBSERVER_EXIT')
    def test_app_timeout(self):
        self.session(app_timeout=True);self.check('UNVERIFIED_APP_TIMEOUT')
    def test_null_exit(self):
        self.session(observer_exit_code=None);self.check('UNVERIFIED_OBSERVER_EXIT')
    def test_hash_pin(self):
        self.session(observer_sha256='0'*64);self.check('UNVERIFIED_OBSERVER_HASH')
    def test_version_pin(self):
        self.session(observer_version='2.5.1');self.check('UNVERIFIED_OBSERVER_VERSION')
    def test_observer_late(self):
        self.session(observer_started_qpc=BASE+FREQ);self.check('UNVERIFIED_LATE_OBSERVER')
    def test_stderr(self):
        (self.p/'presentmon.stderr.txt').write_text('Access denied');refresh(self.p);self.check('UNVERIFIED_OBSERVER_DIAGNOSTICS')
    def test_stdout_warning(self):
        (self.p/'presentmon.stdout.txt').write_text('warning: data loss');refresh(self.p);self.check('UNVERIFIED_OBSERVER_DIAGNOSTICS')
    def test_stdout_event_loss(self):
        (self.p/'presentmon.stdout.txt').write_text('25 events lost');refresh(self.p);self.check('UNVERIFIED_OBSERVER_DIAGNOSTICS')
    def test_no_physical_attestation(self):
        self.session(physical_desktop_attested=False);self.check('UNVERIFIED_ENVIRONMENT')
    def test_identity_mismatch(self):
        self.session(target_pid=5000);self.check('UNVERIFIED_IDENTITY')
    def test_creation_time_mismatch(self):
        self.session(process_creation_filetime='111111');self.check('UNVERIFIED_PROCESS_CREATION')
    def test_frequency_mismatch(self):
        self.session(qpc_frequency=1000);self.check('UNVERIFIED_TIME_AXIS')
    def test_run_id_mismatch(self):
        self.session(run_id='another-run');self.check('UNVERIFIED_RUN_ID')
    def test_sac_block(self):
        self.session(application_launch='BLOCKED_BY_APP_CONTROL');r=self.check('BLOCKED_BY_APP_CONTROL','BLOCKED');self.assertEqual(42,exit_code(r))
    def test_focus_loss(self):
        def change(ev):ev.append(dict(ev[10],event='LOST_FOCUS',qpc=BASE+6*FREQ))
        mutate_events(self.p,change);self.check('FAIL_APP_STATE_CHANGE','FAIL')
    def test_state_false(self):
        mutate_events(self.p,lambda ev:next(e for e in ev if e['event']=='STATE').update(fullscreen=False));self.check('FAIL_DXGI_STATE')
    def test_remote(self):
        mutate_events(self.p,lambda ev:ev[0].update(remote_session=True));self.check('UNVERIFIED_ENVIRONMENT')
    def test_marker_missing(self):
        mutate_events(self.p,lambda ev:ev.__setitem__(slice(None),[e for e in ev if e['event']!='CAPTURE_MARK_END']));self.check('UNVERIFIED_EVENT_CARDINALITY')
    def test_end_missing(self):
        mutate_events(self.p,lambda ev:ev.pop());self.check('UNVERIFIED_EVENT_CARDINALITY')
    def test_marker_kind_mismatch(self):
        mutate_events(self.p,lambda ev:next(e for e in ev if e['event']=='CAPTURE_MARK_END').update(kind='AUTOMATIC_DIAGNOSTIC'));self.check('UNVERIFIED_MARKERS')
    def test_automatic_is_not_recorder(self):
        mutate_events(self.p,lambda ev:[e.update(kind='AUTOMATIC_DIAGNOSTIC') for e in ev if e['event'].startswith('CAPTURE_MARK_')]);r=self.check(verdict='SYNTHETIC_PASS');self.assertEqual('NOT_EVALUATED',r['recorder_result'])
    def test_no_tail(self):
        mutate_events(self.p,lambda ev:next(e for e in ev if e['event']=='CAPTURE_MARK_END').update(qpc=BASE+12*FREQ-1));self.check('UNVERIFIED_INTERVAL_BOUNDS')
    def test_short_interval(self):
        mutate_events(self.p,lambda ev:next(e for e in ev if e['event']=='CAPTURE_MARK_END').update(qpc=BASE+6*FREQ));self.check('UNVERIFIED_SHORT_INTERVAL')
    def test_ledger_gap(self):
        mutate_csv(self.p,lambda rows,fields:rows.pop(100),name='frames.csv');self.check('UNVERIFIED_FRAME_SEQUENCE')
    def test_frame_failed(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(HResult='0x887A0005'),name='frames.csv');self.check('FAIL_PRESENT_LEDGER')
    def test_frame_focus_false(self):
        mutate_csv(self.p,lambda rows,fields:rows[300].update(Focus='0'),name='frames.csv');self.check('FAIL_PRESENT_LEDGER')
    def test_control(self):
        make(self.p,mode='borderless-control',present_mode='Hardware: Independent Flip');self.check('NONEXCLUSIVE_CONTROL_OBSERVED','SYNTHETIC_PASS')
    def test_control_legacy(self):
        make(self.p,mode='borderless-control');self.check('FAIL_CONTROL_LEGACY_OBSERVED','FAIL')
    def test_duplicate_json(self):
        p=self.p/'session.json';p.write_text(p.read_text().replace('"schema": 1','"schema": 1, "schema": 1',1));self.check('UNVERIFIED_DUPLICATE_JSON_KEY')
    def test_unknown_event(self):
        mutate_events(self.p,lambda ev:ev[2].update(event='UNKNOWN_EVENT'));self.check('UNVERIFIED_UNKNOWN_EVENT')
    def test_missing_file(self):
        (self.p/'frames.csv').unlink();self.check('UNVERIFIED_INPUT')
    def test_report_output(self):
        r=self.check();write_report(r,self.p);self.assertTrue((self.p/'summary.txt').exists());self.assertEqual(r,json.loads((self.p/'summary.json').read_text()))
    def test_cli_positive(self):
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,str(root/'tools/verify_presentmon.py'),'--run-dir',str(self.p)],capture_output=True,text=True,timeout=20)
        self.assertEqual(0,r.returncode,r.stderr);self.assertIn('SYNTHETIC_PASS',r.stdout)
    def test_cli_unverified(self):
        (self.p/'presentmon.csv').unlink()
        root=Path(__file__).resolve().parents[1]
        r=subprocess.run([sys.executable,str(root/'tools/verify_presentmon.py'),'--run-dir',str(self.p)],capture_output=True,text=True,timeout=20)
        self.assertEqual(11,r.returncode,r.stderr)

if __name__=='__main__':unittest.main()
