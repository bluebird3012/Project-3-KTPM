import json
import os
import subprocess
from pathlib import Path
from .config import settings

PHP = Path(__file__).with_name('audit.php').read_text()


def bridge(op, **params):
    base, _, _, container = settings()
    payload = dict(op=op, base=base, config=os.getenv('MOODLE_CONFIG_PATH', ''), **params)
    proc = subprocess.run(['docker', 'exec', '-i', container, 'php', '-r', PHP],
                          input=json.dumps(payload), text=True, capture_output=True, timeout=120)
    if proc.returncode or 'NFR_JSON:' not in proc.stdout:
        raise RuntimeError('Moodle CLI audit failed. Check Docker access, config path and wwwroot. '
                           + (proc.stderr or proc.stdout)[-600:])
    result = json.loads(proc.stdout.rsplit('NFR_JSON:', 1)[1].splitlines()[0])
    if not result.get('ok'):
        raise RuntimeError('Audit not successful')
    return result


def audit(prefix, names):
    result = bridge('audit', prefix=prefix, names=list(names))['users']
    return result if isinstance(result, dict) else {}


def exact_user(users, name):
    entries = users.get(name, [])
    return len(entries) == 1 and entries[0]['email'] == name + '@example.invalid'
