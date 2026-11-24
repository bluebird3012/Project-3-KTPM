"""Read-only readiness check; does not create test users."""
import importlib.metadata
import os
from core.config import settings
from core.audit import bridge
from core.moodle_client import session, login, create_form, CREATE, TIMEOUT


def main():
    base,admin,password,container=settings()
    print(f'Target: {base}\nContainer: {container}')
    for pkg in ('requests','beautifulsoup4','locust','python-dotenv'):
        print(f'{pkg}: {importlib.metadata.version(pkg)}')
    a=bridge('capability',username=admin)
    if not a['is_admin'] or not a['can_create'] or a['suspended']:
        raise RuntimeError('Configured account must be an active site admin')
    with session() as c:
        login(c,base,admin,password)
        r=c.get(base+CREATE,timeout=TIMEOUT); r.raise_for_status()
        if not create_form(r): raise RuntimeError('Create form unavailable')
    print('PASS: local Moodle login, form and CLI audit available')
    for role,accepted in [('STUDENT',{'student'}),('TEACHER',{'teacher','editingteacher'})]:
        name=os.getenv(f'MOODLE_{role}_USERNAME',''); pw=os.getenv(f'MOODLE_{role}_PASSWORD','')
        if not name or not pw:
            print(f'SKIP: {role} fixture not configured'); continue
        try:
            v=bridge('capability',username=name)
            if v['can_create'] or v['is_admin'] or v['suspended'] or not accepted.intersection(v['roles']):
                raise RuntimeError('Account role/capability does not meet fixture')
            with session() as c: login(c,base,name,pw)
            print(f'PASS: {role} login and no system create capability')
        except Exception as exc: print(f'NOT READY: {role} ({type(exc).__name__})')

if __name__=='__main__': main()
