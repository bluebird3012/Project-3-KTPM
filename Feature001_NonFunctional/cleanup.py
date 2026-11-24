"""Explicitly remove only recorded synthetic users via Moodle's own delete_user API."""
import argparse
import json
from pathlib import Path
from core.config import ROOT, settings
from core.audit import audit, bridge
from core.reporter import read_jsonl, write_json

def main():
    p=argparse.ArgumentParser(); p.add_argument('run_directory',type=Path); p.add_argument('--apply',action='store_true'); args=p.parse_args()
    path=args.run_directory.resolve()
    if not path.is_relative_to((ROOT/'results').resolve()): raise ValueError('Run must be under project results/')
    info=json.loads((path/'run_info.json').read_text()); base,*_=settings()
    if info['base']!=base: raise ValueError('Run target does not match configured Moodle site')
    names=sorted({e['username'] for f in path.rglob('*.jsonl') for e in read_jsonl(f) if e.get('event')=='attempt'})
    observed=audit(info['prefix'],names)
    print(f'{len(names)} recorded usernames; {sum(map(len,observed.values()))} currently exist.')
    if not args.apply:
        print('Dry-run only. Repeat with --apply to delete only these synthetic accounts.'); return
    result=bridge('cleanup',prefix=info['prefix'],names=names)
    remaining=audit(info['prefix'],names)
    write_json(path/'cleanup.json',{'deleted':result['deleted'],'remaining':remaining})
    print(f"Deleted {len(result['deleted'])}; remaining {len(remaining)}")
    if remaining: raise RuntimeError('Some test accounts remain')

if __name__=='__main__': main()
