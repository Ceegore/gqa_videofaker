#!/usr/bin/env python3
"""Cross-platform structural checks. Not a C++/HLSL/PowerShell compiler."""
from __future__ import annotations
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=['CMakeLists.txt','README.md','AGENTS.md','LICENSES.md','src/main.cpp','src/graphics.cpp',
          'src/diagnostic.cpp','src/scene.cpp','src/shaders.hlsl','src/tiny_font.h',
          'tools/run_test.ps1','tools/start_observer.ps1','tools/verify_presentmon.py',
          'tools/inspect_sac_environment.ps1','.github/workflows/windows-ci.yml']
DOCS=['00_START_HERE','01_FULL_IMPLEMENTATION_PLAN','02_API_CALL_SEQUENCE','03_PRESENTMON_AND_CLASSIFIER',
      '04_OPERATOR_TEST_MANUAL','05_WEAK_AGENT_EXECUTION_RUNBOOK','06_RESEARCH_SOURCES_LICENSES',
      '07_TEST_MATRIX_AND_RELEASE_CHECKLIST','08_TROUBLESHOOTING','09_ASSUMPTIONS_AND_TEST_EVIDENCE',
      '10_SAC_FIRST_DEV_AND_TEST','11_CI_AND_TEST_LAB']

def check(root: Path=ROOT) -> dict[str,int]:
    for f in REQUIRED+[f'docs/{n}.md' for n in DOCS]:
        if not (root/f).is_file() or (root/f).stat().st_size<30:
            raise ValueError('Missing/empty required file: '+f)
    counts={'python_parsed':0,'json_parsed':0,'powershell_encoding_checked':0,'code_files_reviewed':0}
    for p in root.rglob('*'):
        if not p.is_file() or any(x in {'build','dist','.git','__pycache__'} for x in p.relative_to(root).parts):continue
        if p.is_symlink():raise ValueError('Symlink: '+str(p))
        if p.suffix in {'.py','.ps1','.cpp','.h','.hlsl','.md','.json','.csv','.txt','.yml','.manifest'}:
            s=p.read_text(encoding='utf-8-sig')
        else:continue
        if p.suffix=='.py':
            ast.parse(s,filename=str(p));counts['python_parsed']+=1
        if p.suffix=='.json':json.loads(s);counts['json_parsed']+=1
        if p.suffix=='.ps1':
            b=p.read_bytes()
            if not b.startswith(b'\xef\xbb\xbf') or b'\n' in b.replace(b'\r\n',b''):
                raise ValueError('PowerShell requires UTF8 BOM / CRLF for 5.1: '+str(p))
            counts['powershell_encoding_checked']+=1
        if p.suffix in {'.cpp','.h','.hlsl','.ps1','.py'} and 'input_reference' not in p.parts:
            counts['code_files_reviewed']+=1
            # Scan executable PowerShell lines, excluding comments/string documentation.
            if p.suffix=='.ps1':
                for line in s.splitlines():
                    if line.lstrip().startswith('#'):continue
                    if re.search(r'(?i)\b(Set-ExecutionPolicy|Unblock-File|Add-MpPreference|Set-MpPreference|Add-Type)\b|ExecutionPolicy\s+Bypass',line):
                        raise ValueError('Disallowed operation in '+str(p))
    return counts

if __name__=='__main__':
    print(json.dumps(check(),indent=2))
