"""Runs every test script of this level and prints a summary.

    python run_all.py                          # all scripts
    python run_all.py test_fix_and_retry.py    # one script
    ONLY=TC-003-001,TC-003-016 python run_all.py   # only these test cases (any script)
Results: results/results.csv  (+ results/screenshots/<tc_id>.png for failures)
"""
import csv
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RESULTS = os.path.join(HERE, "results")

if __name__ == "__main__":
    shutil.rmtree(RESULTS, ignore_errors=True)
    pattern = sys.argv[1] if len(sys.argv) > 1 else "test_*.py"
    suite = unittest.defaultTestLoader.discover(HERE, pattern=pattern)
    unittest.TextTestRunner(verbosity=1).run(suite)

    path = os.path.join(RESULTS, "results.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print("\n==== SUMMARY ====")
        print(f"test cases run: {len(rows)}  " + "  ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
        for r in rows:
            if r["status"] != "PASS":
                print(f"  {r['tc_id']:<12} {r['status']:<5} {r['message'][:160]}")
        print(f"details: {path}")
