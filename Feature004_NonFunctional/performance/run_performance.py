"""Orchestrator for NFR-07 Performance Testing (Add Quiz under concurrent load)."""
from __future__ import annotations

import argparse
import csv
import math
import os
from statistics import mean, median
import subprocess
import sys
import time

from core.audit import audit_quizzes, bridge, exact_quiz
from core.config import ROOT, settings
from core.moodle_client import TIMEOUT, login, prepare_add_quiz, quiz_created_response, session
from core.reporter import (
    append_json,
    new_quiz_name,
    new_run,
    now,
    read_jsonl,
    write_csv,
    write_json,
)

CRITERIA = {
    "mean_ms_max": 2000.0,
    "p95_ms_max": 5000.0,
    "error_rate_pct_max": 1.0,
    "duplicate_quizzes_max": 0,
}

FIELDS = [
    "users",
    "repeat",
    "duration_seconds",
    "actual_seconds",
    "attempted",
    "completed",
    "created_exactly_once",
    "duplicate_quizzes",
    "setup_errors",
    "http_failures",
    "audit_failures",
    "error_rate_pct",
    "mean_ms",
    "median_ms",
    "p95_ms",
    "max_ms",
    "throughput_per_s",
    "successful_per_s",
    "locust_exit",
    "verdict",
    "reason",
]


def compute_metrics(
    events: list[dict],
    users: int,
    duration: int,
    repeat: int,
    elapsed: float,
    locust_exit: int,
    observed: dict,
    audit_error: str = "",
) -> dict:
    names = [e["quiz_name"] for e in events if e.get("event") == "attempt"]
    results = {e["quiz_name"]: e for e in events if e.get("event") == "result"}
    setup_errors = sum(e.get("event") == "setup_error" for e in events)
    duplicate_attempts = len(names) - len(set(names))
    duplicate_db = sum(max(0, len(observed.get(n, [])) - 1) for n in set(names))
    duplicates = duplicate_attempts + duplicate_db

    complete = [results[n] for n in names if n in results]
    timings = sorted(float(r["response_ms"]) for r in complete)
    verified = sum(exact_quiz(observed, n) for n in names)
    successful = sum(
        n in results and bool(results[n].get("http_ok")) and exact_quiz(observed, n)
        for n in names
    )
    http_failures = sum(not bool(results.get(n, {}).get("http_ok", False)) for n in names)
    audit_failures = len(names) - verified
    denominator = len(names) + setup_errors
    error_rate = round((denominator - successful) / denominator * 100.0, 3) if denominator else None

    avg = round(mean(timings), 3) if timings else None
    med = round(median(timings), 3) if timings else None
    p95 = round(timings[math.ceil(0.95 * len(timings)) - 1], 3) if timings else None
    max_v = round(max(timings), 3) if timings else None

    if audit_error or locust_exit not in (0, 1) or len(complete) != len(names):
        verdict, reason = "INCONCLUSIVE", audit_error or f"Incomplete workload or process error (exit={locust_exit})"
    elif not names and setup_errors == 0:
        verdict, reason = "INCONCLUSIVE", "No POST attempts or setup events recorded within window"
    elif not names and setup_errors > 0:
        verdict, reason = "FAIL", f"All virtual users failed during setup ({setup_errors} setup errors)"
    else:
        reasons = []
        if avg is None or avg > CRITERIA["mean_ms_max"]:
            reasons.append(f"Mean {avg}ms > {CRITERIA['mean_ms_max']}ms")
        if p95 is None or p95 > CRITERIA["p95_ms_max"]:
            reasons.append(f"P95 {p95}ms > {CRITERIA['p95_ms_max']}ms")
        if error_rate is None or error_rate > CRITERIA["error_rate_pct_max"]:
            reasons.append(f"ErrorRate {error_rate}% > {CRITERIA['error_rate_pct_max']}%")
        if duplicates > CRITERIA["duplicate_quizzes_max"]:
            reasons.append(f"Duplicates={duplicates} > 0")
        if audit_failures > 0:
            reasons.append(f"AuditFailures={audit_failures}")
        if reasons:
            verdict, reason = "FAIL", "; ".join(reasons)
        else:
            verdict, reason = "PASS", "All proposed thresholds met"

    return {
        "users": users,
        "repeat": repeat,
        "duration_seconds": duration,
        "actual_seconds": round(elapsed, 3),
        "attempted": len(names),
        "completed": len(complete),
        "created_exactly_once": verified,
        "duplicate_quizzes": duplicates,
        "setup_errors": setup_errors,
        "http_failures": http_failures,
        "audit_failures": audit_failures,
        "error_rate_pct": error_rate,
        "mean_ms": avg,
        "median_ms": med,
        "p95_ms": p95,
        "max_ms": max_v,
        "throughput_per_s": round(len(complete) / elapsed, 4) if elapsed else 0.0,
        "successful_per_s": round(successful / elapsed, 4) if elapsed else 0.0,
        "locust_exit": locust_exit,
        "verdict": verdict,
        "reason": reason,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="NFR-07 Performance Testing (Add Quiz) on local Moodle")
    parser.add_argument("--smoke", action="store_true", help="Run smoke workload: 1 user x 15s x 1 repeat")
    args = parser.parse_args(argv)

    cfg = settings()
    base = cfg["base"]
    admin = cfg["username"]
    password = cfg["password"]
    course_id = cfg["course_id"]
    section_id = cfg["section_id"]

    cap = bridge("capability", username=admin)
    if not cap.get("can_add_quiz") or cap.get("suspended"):
        raise RuntimeError(f"Configured user {admin!r} cannot add quizzes in course={course_id}")

    directory, info = new_run(
        "performance",
        base,
        extra={
            "nfr_id": "NFR-07",
            "smoke": args.smoke,
            "course_id": course_id,
            "section_id": section_id,
            "container": cfg["container"],
            "moodle_release": cap.get("release", ""),
        },
    )
    prefix = info["prefix"]
    preflight_log = directory / "preflight.jsonl"
    pf_name = new_quiz_name(prefix)

    # Preflight: validate real HTTP Add Quiz creation AND independent MariaDB audit before load
    print(f"Preflight check ({pf_name})...", flush=True)
    try:
        if audit_quizzes(prefix, [pf_name]):
            raise RuntimeError("Unexpected pre-existing quiz in run namespace")
        with session() as client:
            login(client, base, admin, password)
            url, data = prepare_add_quiz(client, base, pf_name, course_id=course_id, section_id=section_id)
            append_json(preflight_log, {"event": "attempt", "quiz_name": pf_name})
            t0 = time.perf_counter()
            resp = client.post(url, data=data, timeout=TIMEOUT)
            pf_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            http_ok = quiz_created_response(resp, pf_name)
            obs = audit_quizzes(prefix, [pf_name])
            db_ok = exact_quiz(obs, pf_name)
            append_json(
                preflight_log,
                {
                    "event": "result",
                    "quiz_name": pf_name,
                    "http_ok": http_ok,
                    "db_ok": db_ok,
                    "status": resp.status_code,
                    "response_ms": pf_ms,
                },
            )
            if not http_ok or not db_ok:
                raise RuntimeError(f"Preflight failed (http_ok={http_ok}, db_ok={db_ok}, status={resp.status_code})")
        info["preflight"] = "PASS"
        info["preflight_ms"] = pf_ms
        write_json(directory / "run_info.json", info)
        print(f"Preflight PASS ({pf_ms:.1f} ms; DB verified)", flush=True)
    except Exception as exc:
        info.update(preflight="ERROR", complete=False, finished_at=now(), error=str(exc))
        write_json(directory / "run_info.json", info)
        print(f"Preflight FAILED: {exc}\nEvidence: {directory}", flush=True)
        return 2

    if args.smoke:
        plan = [(1, 15, 1, 1)]
    else:
        plan = []
        with (ROOT / "performance" / "config.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                plan.append(tuple(int(row[k]) for k in ("users", "duration_seconds", "repetitions", "spawn_rate")))

    if not plan or len(plan) > 4 or any(
        not (1 <= u <= 20 and 1 <= d <= 60 and 1 <= r <= 3 and 1 <= s <= u) for u, d, r, s in plan
    ):
        raise ValueError("Load plan exceeds bounded local test limits")

    summary: list[dict] = []
    for users, duration, reps, spawn in plan:
        for repeat in range(1, reps + 1):
            sub = directory / f"u{users:02d}_r{repeat}"
            sub.mkdir()
            log = sub / "attempts.jsonl"
            env = dict(os.environ, NFR_PREFIX=prefix, NFR_MANIFEST=str(log))
            cmd = [
                sys.executable,
                "-m",
                "locust",
                "-f",
                str(ROOT / "performance" / "locustfile.py"),
                "--headless",
                "--host",
                base,
                "-u",
                str(users),
                "-r",
                str(spawn),
                "--run-time",
                f"{duration}s",
                "--stop-timeout",
                "120",
                "--csv",
                str(sub / "locust"),
                "--csv-full-history",
                "--only-summary",
            ]
            print(f"Load: {users} users | repeat {repeat}/{reps} | {duration}s ...", flush=True)
            t_start = time.monotonic()
            try:
                with (sub / "locust.log").open("w", encoding="utf-8") as out:
                    proc = subprocess.run(
                        cmd,
                        cwd=ROOT,
                        env=env,
                        stdout=out,
                        stderr=subprocess.STDOUT,
                        timeout=duration + 240,
                    )
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = 124
            elapsed = time.monotonic() - t_start

            events = read_jsonl(log)
            names = [e["quiz_name"] for e in events if e.get("event") == "attempt"]
            observed: dict = {}
            audit_err = ""
            try:
                observed = audit_quizzes(prefix, names)
                write_json(sub / "audit.json", observed)
            except Exception as exc:
                audit_err = f"Audit error: {type(exc).__name__}: {str(exc)[:180]}"

            row = compute_metrics(events, users, duration, repeat, elapsed, code, observed, audit_err)
            summary.append(row)
            write_csv(directory / "summary.csv", summary, FIELDS)

            res_map = {e["quiz_name"]: e for e in events if e.get("event") == "result"}
            req_rows = [
                {
                    "quiz_name": n,
                    "status": res_map.get(n, {}).get("status", ""),
                    "response_ms": res_map.get(n, {}).get("response_ms", ""),
                    "http_ok": res_map.get(n, {}).get("http_ok", False),
                    "db_count": len(observed.get(n, [])),
                    "db_exact": exact_quiz(observed, n) if not audit_err else "",
                    "error": res_map.get(n, {}).get("error", ""),
                }
                for n in names
            ]
            write_csv(
                sub / "requests.csv",
                req_rows,
                ["quiz_name", "status", "response_ms", "http_ok", "db_count", "db_exact", "error"],
            )
            print(
                f"  -> {row['verdict']} | attempted={row['attempted']} | verified={row['created_exactly_once']} | "
                f"mean={row['mean_ms']}ms | p95={row['p95_ms']}ms | err={row['error_rate_pct']}% | {row['reason']}",
                flush=True,
            )
            time.sleep(2)

    if any(r["verdict"] == "INCONCLUSIVE" for r in summary):
        overall = "INCONCLUSIVE"
    elif any(r["verdict"] == "FAIL" for r in summary):
        overall = "FAIL"
    else:
        overall = "PASS"

    info.update(
        complete=True,
        finished_at=now(),
        verdict=overall,
        runs=len(summary),
        criteria=CRITERIA,
    )
    write_json(directory / "run_info.json", info)
    print(f"\nNFR-07 Results: {directory}\nOverall Verdict: {overall}" + (" (smoke)" if args.smoke else ""), flush=True)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
