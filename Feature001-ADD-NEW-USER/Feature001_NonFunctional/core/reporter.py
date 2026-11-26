import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .config import ROOT


def new_run(kind, base):
    token = uuid.uuid4().hex[:12]
    directory = ROOT / 'results' / kind / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+token)
    directory.mkdir(parents=True)
    info = {'kind':kind, 'base':base, 'prefix':'nfr'+token+'_', 'started_at':now()}
    write_json(directory/'run_info.json', info)
    return directory, info


def now():
    return datetime.now(timezone.utc).isoformat()


def new_name(prefix):
    return prefix + uuid.uuid4().hex[:16]


def append_json(path, row):
    with open(path,'a',encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False)+'\n')


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def write_csv(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
