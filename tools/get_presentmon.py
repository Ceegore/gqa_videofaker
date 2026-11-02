#!/usr/bin/env python3
"""Explicit download to one FILE. Never installs, launches, unblocks or changes policy."""
from __future__ import annotations
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Callable, Any

LIMIT=20_000_000

def download_verified(lock: dict[str, Any], target: Path, opener: Callable=urllib.request.urlopen) -> Path:
    if target.exists():
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=lock['sha256']:
            raise ValueError('Refusing to overwrite an existing path with a different digest')
        return target
    request=urllib.request.Request(lock['url'],headers={'User-Agent':'FSEProbe-explicit-download/0.1'})
    with opener(request,timeout=45) as response:
        data=response.read(LIMIT+1)
    if len(data)>LIMIT or hashlib.sha256(data).hexdigest()!=lock['sha256']:
        raise ValueError('Download exceeds size limit or SHA256 mismatch; not written')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:
        stream.write(data)
    return target

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Exact destination filename, not a directory')
    parser.add_argument('--download',action='store_true',help='Consent to download the pinned binary')
    args=parser.parse_args()
    if not args.download:
        parser.error('Explicit --download required; no network request made')
    lock=json.loads(Path(__file__).with_name('presentmon.lock.json').read_text(encoding='utf-8'))
    target=download_verified(lock,args.output)
    print(str(target)+' - digest matched; not launched; SAC acceptance unverified.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
