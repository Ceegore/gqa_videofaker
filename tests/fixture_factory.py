"""Generate explicitly SYNTHETIC traces, with QPC values above IEEE754 exact range."""
import csv
import json
from pathlib import Path
from tools.verify_presentmon import PM_SHA256, EVIDENCE_FILES, sha
BASE=9_007_199_254_740_992 + 100_000_000
FREQ=10_000_000
PID=4242

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2)+'\n',encoding='utf-8')

def refresh(path: Path):
    session=json.loads((path/'session.json').read_text(encoding='utf-8'))
    session['evidence_sha256']={name:sha(path/name) for name in EVIDENCE_FILES if (path/name).exists()}
    write_json(path/'session.json',session)

def make(path: Path, mode='legacy-exclusive', present_mode='Hardware: Legacy Flip'):
    path.mkdir(parents=True,exist_ok=True)
    event=[]
    def add(seconds, name, **kw):
        event.append(dict(schema=1,qpc=BASE+int(seconds*FREQ),utc='2026-11-02T12:00:00.000Z',event=name,**kw))
    desired=mode=='legacy-exclusive'
    add(0,'START',run_id='synthetic-fixture',pid=PID,process_creation_filetime='134380944000000000',qpc_frequency=FREQ,
        version='0.1.0',mode=mode,load='low',duration=15,warmup=3,fps_cap=60,auto_mark=False,remote_session=False,session_id=1)
    add(.01,'DISPLAY_SELECTED',gpu='SYNTHETIC GPU - NOT MEASURED',output='SYNTHETIC DISPLAY')
    if desired:
        add(.5,'REQUEST_FULLSCREEN');add(.6,'SET_FULLSCREEN_RESULT',hresult='0x0')
    add(1,'MODE_READY',fullscreen=desired,focus=True,correct_output=True,swapchain_pointer_diagnostic='0x123400')
    for quarter in range(5,47):
        add(quarter/4,'STATE',fullscreen=desired,focus=True,correct_output=True)
    add(4,'CAPTURE_MARK_START',kind='OPERATOR_MARKED')
    add(9,'CAPTURE_MARK_END',kind='OPERATOR_MARKED')
    add(11.98,'LEAVE_FULLSCREEN_RESULT',hresult='0x0');add(12,'END',exit_code=0,live_verification='NOT_LIVE_VERIFIED')
    event.sort(key=lambda e:e['qpc'])
    for i,e in enumerate(event):e['seq']=i
    (path/'app.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in event),encoding='utf-8')
    with (path/'frames.csv').open('w',newline='',encoding='utf-8') as f, (path/'presentmon.csv').open('w',newline='',encoding='utf-8') as pm:
        fw=csv.writer(f);pw=csv.writer(pm)
        fw.writerow(['FrameIndex','BeforeQPC','AfterQPC','HResult','Fullscreen','Focus'])
        pw.writerow(['Application','ProcessID','SwapChainAddress','PresentRuntime','PresentMode','CPUStartQPC','MsCPUBusy','DisplayedTime'])
        for i in range(650):
            before=BASE+FREQ+100_000+i*166_667
            fw.writerow([i,before,before+50_000,'0x0',int(desired),1])
            pw.writerow(['FSEProbe.exe',PID,'0x123400','DXGI',present_mode,before-10_000,'1.01','16.6667'])
    (path/'presentmon.stdout.txt').write_text('',encoding='utf-8')
    (path/'presentmon.stderr.txt').write_text('',encoding='utf-8')
    write_json(path/'session.json',dict(schema=1,run_id='synthetic-fixture',application_launch='STARTED',
        mode=mode,target_pid=PID,process_creation_filetime='134380944000000000',qpc_frequency=FREQ,
        observer_started_qpc=BASE-FREQ,observer_sha256=PM_SHA256,observer_version='2.6.0',time_axis='qpc_ticks_v2',
        observer_exit_code=0,observer_timeout=False,app_exit_code=0,app_timeout=False,
        physical_desktop_attested=True,evidence_kind='SYNTHETIC_FIXTURE'))
    refresh(path)
    return path

def mutate_csv(path, fn, name='presentmon.csv'):
    file=path/name
    with file.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=list(reader.fieldnames);records=list(reader)
    fn(records,fields)
    with file.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(records)
    refresh(path)

def mutate_events(path, fn):
    file=path/'app.jsonl'
    event=[json.loads(line) for line in file.read_text(encoding='utf-8').splitlines()]
    fn(event)
    event.sort(key=lambda e:e['qpc'])
    for i,e in enumerate(event):e['seq']=i
    file.write_text(''.join(json.dumps(e)+'\n' for e in event),encoding='utf-8')
    refresh(path)
