"""Local, authorized Moodle security regression; all generated accounts are synthetic."""
import csv
import os
import secrets
from copy import deepcopy
from urllib.parse import urljoin
from core.config import ROOT, settings
from core.audit import audit, bridge, exact_user
from core.moodle_client import login, prepare, success, session, sesskey, create_form, denial, soup, checked_url, override, CREATE, TIMEOUT
from core.reporter import new_run, new_name, now, append_json, read_jsonl, write_csv, write_json

FIELDS=['case_id','scenario','expected','status','final_path','form_visible','denial_observed','username','db_count','verdict','reason']

class Blocked(Exception): pass


def role_session(base, role):
    username=os.getenv(f'MOODLE_{role}_USERNAME',''); password=os.getenv(f'MOODLE_{role}_PASSWORD','')
    if not username or not password: raise Blocked(f'Configure dedicated {role} credentials')
    cap=bridge('capability',username=username)
    if cap['can_create'] or cap['is_admin'] or cap['suspended'] or not (set(cap['roles']) & ({'student'} if role=='STUDENT' else {'teacher','editingteacher'})):
        raise Blocked(f'{role} fixture must have the named role and no system user:create capability')
    c=session()
    try:
        r=login(c,base,username,password)
        token=sesskey(r) or sesskey(c.get(base+'/',timeout=TIMEOUT))
        if not token: raise RuntimeError('Restricted session key not observed')
        return c,token
    except Exception:
        c.close(); raise


def execute(case, base, admin, password, prefix, manifest):
    from urllib.parse import urlsplit
    caseid=case['case_id']; row=dict(case); name=''; response=None; clients=[]
    def fresh():
        c=session(); clients.append(c); return c
    def authenticated():
        c=fresh(); login(c,base,admin,password); return c
    try:
        if caseid in ('SEC-01','SEC-02','SEC-03'):
            if caseid=='SEC-01': c=fresh()
            else:
                c,_=role_session(base,'STUDENT' if caseid=='SEC-02' else 'TEACHER'); clients.append(c)
            response=c.get(base+CREATE,timeout=TIMEOUT)
            visible=bool(create_form(response)); denied=denial(response)
            if visible: verdict,reason='FAIL','Create form accessible'
            elif denied and response.status_code<500: verdict,reason='PASS','Access denied or redirected to login'
            else: verdict,reason='INCONCLUSIVE','No form but denial not established'
            row.update(form_visible=visible,denial_observed=denied)
        else:
            name=new_name(prefix); row['username']=name
            if audit(prefix,[name]): raise RuntimeError('Unexpected pre-existing test account')
            a=authenticated(); url,data=prepare(a,base,name)
            if caseid=='SEC-04': c=fresh(); data=override(data,sesskey=None)
            elif caseid=='SEC-05':
                # Restricted account with own legitimate session token, not an admin token.
                try: c,token=role_session(base,'STUDENT')
                except Blocked: c,token=role_session(base,'TEACHER')
                clients.append(c); data=override(data,sesskey=token)
            elif caseid=='SEC-06': c=a; data=override(data,sesskey=None)
            elif caseid=='SEC-07': c=a; data=override(data,sesskey='invalid_'+secrets.token_hex(8))
            elif caseid=='SEC-08':
                c=fresh(); c.cookies=deepcopy(a.cookies)
                token=dict(data)['sesskey']
                a.get(base+'/login/logout.php',params={'sesskey':token},timeout=TIMEOUT)
                check=a.get(base+CREATE,timeout=TIMEOUT)
                if create_form(check) or not denial(check): raise RuntimeError('Logout not confirmed')
            elif caseid=='SEC-09':
                c=fresh(); c.cookies=deepcopy(a.cookies)
                cookies=[cookie for cookie in c.cookies if cookie.name.lower().startswith('moodlesession')]
                if not cookies: raise Blocked('MoodleSession cookie not identified')
                for cookie in cookies: c.cookies.set(cookie.name,'invalid_'+secrets.token_hex(16),domain=cookie.domain,path=cookie.path)
            elif caseid=='SEC-10': c=a
            else: raise ValueError('Unknown security case')
            append_json(manifest,{'event':'attempt','username':name,'case_id':caseid})
            response=c.post(url,data=data,timeout=TIMEOUT)
            observed=audit(prefix,[name]); count=len(observed.get(name,[])); row['db_count']=count
            row['denial_observed']=denial(response); row['form_visible']=bool(create_form(response))
            if caseid=='SEC-10':
                if exact_user(observed,name) and success(response): verdict,reason='PASS','Positive control: success alert and exact DB user'
                else: verdict,reason='INCONCLUSIVE','Positive control did not establish a valid creation request'
            elif count: verdict,reason='FAIL','Unauthorized test account exists'
            elif response.status_code>=500 or response.status_code==0: verdict,reason='INCONCLUSIVE','Server/transport error; no account observed'
            else: verdict,reason='PASS','No account created (independent DB audit)'
        row.update(verdict=verdict,reason=reason)
    except Blocked as exc: row.update(verdict='SKIP',reason=str(exc))
    except Exception as exc:
        row.update(verdict='INCONCLUSIVE',reason=type(exc).__name__+': '+str(exc)[:300])
        # Even if a response times out, check whether the server created the account.
        if name and any(e for e in read_jsonl(manifest) if e.get('username')==name):
            try:
                count=len(audit(prefix,[name]).get(name,[])); row['db_count']=count
                if count and caseid!='SEC-10': row.update(verdict='FAIL',reason='Unauthorized account exists despite request exception')
            except Exception: pass
    finally:
        if response is not None:
            row.update(status=response.status_code,final_path=urlsplit(response.url).path)
        for c in clients: c.close()
    return row


def main():
    base,admin,password,_=settings()
    cap=bridge('capability',username=admin)
    if not cap['can_create'] or not cap['is_admin']: raise RuntimeError('An actual Moodle test administrator is required')
    directory,info=new_run('security',base); manifest=directory/'attempts.jsonl'
    with (ROOT/'security/security_cases.csv').open() as f: cases=list(csv.DictReader(f))
    control=next(c for c in cases if c['case_id']=='SEC-10')
    # Positive control first: if invalid payload, no negative PASS is credited.
    result=execute(control,base,admin,password,info['prefix'],manifest); rows=[result]
    print(f"SEC-10: {result['verdict']} - {result['reason']}")
    for case in cases:
        if case['case_id']=='SEC-10': continue
        row=execute(case,base,admin,password,info['prefix'],manifest) if result['verdict']=='PASS' else dict(case,verdict='SKIP',reason='Positive control failed')
        rows.append(row); print(f"{row['case_id']}: {row['verdict']} - {row['reason']}",flush=True)
        write_csv(directory/'results.csv',sorted(rows,key=lambda r:r['case_id']),FIELDS)
    negative=[r for r in rows if r['case_id']!='SEC-10']; counts={v:sum(r['verdict']==v for r in rows) for v in ('PASS','FAIL','SKIP','INCONCLUSIVE')}
    verdict='FAIL' if counts['FAIL'] else 'PASS' if counts['PASS']==10 else 'INCONCLUSIVE'
    tested=sum(r['verdict'] in ('PASS','FAIL') for r in negative)
    info.update(complete=True,finished_at=now(),verdict=verdict,counts=counts,negative_tested=tested,
                negative_pass_rate_pct=(100*sum(r['verdict']=='PASS' for r in negative)/tested if tested else None),
                unauthorized_creations=sum(int(r.get('db_count',0)) for r in negative),positive_control=result['verdict'])
    write_json(directory/'run_info.json',info); print(f'Results: {directory}\nVerdict: {verdict}')
    return 0 if verdict=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
