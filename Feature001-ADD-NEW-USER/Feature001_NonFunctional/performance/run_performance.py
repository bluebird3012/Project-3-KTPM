import argparse
import csv
import math
import os
import subprocess
import sys
import time
from statistics import mean, median
from pathlib import Path
from core.config import ROOT, settings
from core.audit import audit, exact_user, bridge
from core.moodle_client import login, prepare, success, session, TIMEOUT
from core.reporter import new_run, new_name, now, append_json, read_jsonl, write_csv, write_json

FIELDS = ['users','repeat','duration_seconds','actual_seconds','attempted','completed','created_exactly_once',
          'setup_errors','http_failures','audit_failures','error_rate_pct','mean_ms','median_ms','p95_ms',
          'max_ms','throughput_per_s','successful_per_s','locust_exit','verdict','reason']


def metrics(events, users, duration, repeat, elapsed, locust_exit, observed, audit_error=''):
    names = [e['username'] for e in events if e['event']=='attempt']
    results = {e['username']:e for e in events if e['event']=='result'}
    setup_errors = sum(e['event']=='setup_error' for e in events)
    duplicate = len(names)-len(set(names))
    complete = [results[n] for n in names if n in results]
    timings = sorted(r['response_ms'] for r in complete)
    verified = sum(exact_user(observed,n) for n in names)
    successful = sum(n in results and results[n]['http_ok'] and exact_user(observed,n) for n in names)
    http_failures = sum(not results.get(n,{}).get('http_ok',False) for n in names)
    audit_failures = len(names)-verified
    denominator = len(names)+setup_errors
    rate = (denominator-successful)/denominator*100 if denominator else None
    avg = mean(timings) if timings else None
    p95 = timings[math.ceil(.95*len(timings))-1] if timings else None
    if audit_error or not names or not timings or locust_exit not in (0,1) or len(complete)!=len(names):
        verdict,reason='INCONCLUSIVE', audit_error or 'Incomplete workload or process error'
    else:
        passed=avg<=2000 and p95<=5000 and rate<=1 and duplicate==0 and all(len(observed.get(n,[]))<=1 for n in names)
        verdict,reason=('PASS','All proposed thresholds met') if passed else ('FAIL','One or more proposed thresholds exceeded')
    return dict(users=users,repeat=repeat,duration_seconds=duration,actual_seconds=round(elapsed,3),
                attempted=len(names),completed=len(complete),created_exactly_once=verified,setup_errors=setup_errors,
                http_failures=http_failures,audit_failures=audit_failures,error_rate_pct=rate,mean_ms=avg,
                median_ms=median(timings) if timings else None,p95_ms=p95,max_ms=max(timings) if timings else None,
                throughput_per_s=len(complete)/elapsed if elapsed else 0,successful_per_s=successful/elapsed if elapsed else 0,
                locust_exit=locust_exit,verdict=verdict,reason=reason)


def main():
    parser=argparse.ArgumentParser(description='Local Moodle load test; no remote target allowed.')
    parser.add_argument('--smoke',action='store_true',help='One user, 10 seconds, one repetition; not formal NFR result')
    args=parser.parse_args()
    base,admin,password,_=settings()
    if not bridge('capability',username=admin)['can_create']:
        raise RuntimeError('Configured admin cannot create users')
    directory,info=new_run('performance',base)
    prefix=info['prefix']; info['smoke']=args.smoke
    manifest=directory/'preflight.jsonl'
    name=new_name(prefix)
    # Validate the real form submission and DB verification before load.
    try:
        if audit(prefix,[name]): raise RuntimeError('Unexpected pre-existing test account')
        with session() as client:
            login(client,base,admin,password); url,data=prepare(client,base,name)
            append_json(manifest,{'event':'attempt','username':name})
            response=client.post(url,data=data,timeout=TIMEOUT)
            if not success(response) or not exact_user(audit(prefix,[name]),name):
                raise RuntimeError('Preflight POST did not produce success alert and exact user record')
        info['preflight']='PASS'; write_json(directory/'run_info.json',info)
    except Exception as exc:
        info.update(preflight='ERROR',complete=False,finished_at=now(),error=str(exc)); write_json(directory/'run_info.json',info)
        print(f'Preflight failed. Evidence: {directory}'); return 2
    plan=[(1,10,1,1)] if args.smoke else []
    if not args.smoke:
        with (ROOT/'performance/config.csv').open() as f:
            for row in csv.DictReader(f):
                plan.append(tuple(int(row[k]) for k in ('users','duration_seconds','repetitions','spawn_rate')))
    if any(not (1<=u<=20 and 1<=d<=60 and 1<=r<=3 and 1<=s<=u) for u,d,r,s in plan) or not plan or len(plan)>4:
        raise ValueError('Load plan exceeds bounded local test limits')
    summary=[]
    for users,duration,reps,spawn in plan:
        for repeat in range(1,reps+1):
            sub=directory/f'u{users:02d}_r{repeat}'; sub.mkdir()
            log=sub/'attempts.jsonl'
            env=dict(os.environ,NFR_PREFIX=prefix,NFR_MANIFEST=str(log))
            command=[sys.executable,'-m','locust','-f',str(ROOT/'performance/locustfile.py'),'--headless','--host',base,
                     '-u',str(users),'-r',str(spawn),'--run-time',f'{duration}s','--stop-timeout','20',
                     '--csv',str(sub/'locust'),'--csv-full-history','--only-summary']
            start=time.monotonic()
            print(f'Load: {users} users / repetition {repeat} / {duration}s',flush=True)
            try:
                with (sub/'locust.log').open('w') as out:
                    p=subprocess.run(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=duration+90)
                code=p.returncode
            except subprocess.TimeoutExpired:
                code=124
            elapsed=time.monotonic()-start
            events=read_jsonl(log); names=[e['username'] for e in events if e['event']=='attempt']
            observed={}; error=''
            try:
                observed=audit(prefix,names); write_json(sub/'audit.json',observed)
            except Exception as exc:
                error=f'Audit error: {type(exc).__name__}'
            row=metrics(events,users,duration,repeat,elapsed,code,observed,error)
            summary.append(row); write_csv(directory/'summary.csv',summary,FIELDS)
            results={e['username']:e for e in events if e['event']=='result'}
            write_csv(sub/'requests.csv',[dict(username=n,**{k:v for k,v in results.get(n,{}).items() if k!='username'},
                db_count=len(observed.get(n,[])),db_exact=exact_user(observed,n) if not error else '') for n in names],
                ['username','status','response_ms','http_ok','db_count','db_exact','error'])
            print(f"  {row['verdict']} | POST={row['attempted']} | P95={row['p95_ms']} ms | error={row['error_rate_pct']}%",flush=True)
            time.sleep(2)
    verdict='INCONCLUSIVE' if any(r['verdict']=='INCONCLUSIVE' for r in summary) else 'FAIL' if any(r['verdict']=='FAIL' for r in summary) else 'PASS'
    info.update(complete=True,finished_at=now(),verdict=verdict,runs=len(summary),criteria={'mean_ms_max':2000,'p95_ms_max':5000,'error_rate_pct_max':1,'duplicate_accounts_max':0})
    write_json(directory/'run_info.json',info)
    print(f'Results: {directory}\nVerdict: {verdict}'+(' (smoke only)' if args.smoke else ''))
    return 0 if verdict=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
