#!/usr/bin/env python3
"""Package an already built Windows executable; never compiles, signs or executes it."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

EXCLUDED = {'__pycache__', '.git', 'logs', 'build', 'dist'}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def manifest(root: Path) -> dict[str, str]:
    files = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError(f'Symlink forbidden: {p}')
        if p.is_file() and p.name != 'SHA256SUMS.json':
            name = p.relative_to(root).as_posix()
            files[name] = digest(p.read_bytes())
    (root/'SHA256SUMS.json').write_text(json.dumps(files, indent=2)+'\n', encoding='utf-8')
    return files

def verify_zip(path: Path) -> int:
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) != len({n.casefold() for n in names}):
            raise ValueError('Duplicate or case-colliding archive names')
        for item in z.infolist():
            n = item.filename
            if n.startswith('/') or '\\' in n or ':' in n or any(v in {'', '.', '..'} for v in n.split('/')):
                raise ValueError(f'Unsafe archive path: {n}')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP symlink forbidden')
        index = json.loads(z.read('SHA256SUMS.json'))
        if set(index) != set(names)-{'SHA256SUMS.json'}:
            raise ValueError('Manifest membership mismatch')
        for name, expected in index.items():
            if digest(z.read(name)) != expected:
                raise ValueError(f'Hash mismatch: {name}')
        return len(names)

def pack(root: Path, output: Path) -> int:
    output = output.resolve()
    if output.is_relative_to(root.resolve()):
        raise ValueError('ZIP output must be outside the packaged source tree')
    index = manifest(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted([*index, 'SHA256SUMS.json']):
            item = zipfile.ZipInfo(name, (2026,11,2,0,0,0))
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, (root/name).read_bytes())
    count = verify_zip(output)
    output.with_suffix(output.suffix+'.sha256').write_text(digest(output.read_bytes())+'  '+output.name+'\n', encoding='ascii')
    return count

def validate_pe(exe: Path) -> None:
    b = exe.read_bytes()
    if len(b)<128 or b[:2]!=b'MZ':
        raise ValueError('Not a PE executable')
    offset = struct.unpack_from('<I', b, 0x3c)[0]
    if offset+26 > len(b) or b[offset:offset+4]!=b'PE\x00\x00':
        raise ValueError('Invalid PE header')
    if struct.unpack_from('<H', b, offset+4)[0]!=0x8664 or struct.unpack_from('<H', b, offset+24)[0]!=0x20b:
        raise ValueError('Expected AMD64 PE32+ executable')

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exe',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--ci-build-pass',action='store_true',help='Set only after the Windows CI build and all offline gates really passed')
    a=ap.parse_args()
    validate_pe(a.exe)
    source=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='fse-release-') as d:
        stage=Path(d)
        (stage/'bin').mkdir()
        shutil.copy2(a.exe,stage/'bin/FSEProbe.exe')
        for folder in ('tools','docs','schemas','licenses'):
            shutil.copytree(source/folder,stage/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ('LICENSES.md','AGENTS.md'):
            shutil.copy2(source/name,stage/name)
        (stage/'README.md').write_text('''# FSEProbe Windows-Runtimepaket

Dieses Paket wurde aus einem Windows-Build erstellt. Maßgeblich ist BUILD_STATUS.json.
Es ist nicht durch diesen Packager signiert und beweist weder SAC-Zulassung noch physisches FSE.

Start: docs/00_START_HERE.md, Sicherheit: docs/10_SAC_FIRST_DEV_AND_TEST.md.
Die EXE liegt unter bin/FSEProbe.exe. PresentMon wird separat hashgeprüft bezogen.
Für Änderungen, CI und Agententickets das vollständige Quellkit verwenden; dessen src/, tests/,
input_reference/ und Erstellungsbelege sind absichtlich nicht in diesem Runtimepaket enthalten.
AGENTS.md beschreibt die verbindlichen Regeln für diese Quellarbeit.
''', encoding='utf-8')
        status={
            'schema':1,'version':'0.1.0-kit','ci_build_status':'PASS' if a.ci_build_pass else 'NOT_ATTESTED',
            'binary_signature':'NOT_SIGNED_BY_THIS_PACKAGER', 'sac_execution':'NOT_VERIFIED',
            'hardware_fse_validation':'NOT_EXECUTED','recorder_result':'NOT_EVALUATED',
            'exe_sha256':digest(a.exe.read_bytes())}
        (stage/'BUILD_STATUS.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
        count=pack(stage,a.output)
    print(f'PACKAGED {count} files. No SAC or FSE hardware claim: {a.output}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
