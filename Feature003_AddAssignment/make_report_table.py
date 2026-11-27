"""Fills the results table of REPORT_SECTION.md from the results/results.csv files.

    python make_report_table.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = [("Level 1", "Level1"), ("Level 2", "Level2"), ("Non-functional", "NonFunctional")]
START, END = "<!-- RESULTS START -->", "<!-- RESULTS END -->"


def read(folder):
    path = os.path.join(HERE, folder, "results", "results.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    latest = {}                       # a test case run twice: keep the latest result
    for r in rows:
        latest[r["tc_id"]] = r
    return list(latest.values())


lines = [START, "", "| Part | Checks run | PASS | FAIL | ERROR |", "|---|---|---|---|---|"]
details = []
for label, folder in PARTS:
    rows = read(folder)
    count = lambda s: sum(1 for r in rows if r["status"] == s)
    lines.append(f"| {label} | {len(rows)} | {count('PASS')} | {count('FAIL')} | {count('ERROR')} |")
    for r in rows:
        if r["status"] != "PASS":
            details.append(f"| {label} | {r['tc_id']} | {r['title']} | {r['status']} | {r['message'][:180].replace('|', '/')} |")
lines += ["", "Test cases that did not pass (reason from `results/results.csv`; see README §4 for the analysis):", "",
          "| Part | ID | Title | Status | Message |", "|---|---|---|---|---|"] + details
perf = os.path.join(HERE, "NonFunctional", "results", "performance_measurements.csv")
if os.path.exists(perf):
    with open(perf, encoding="utf-8-sig") as f:
        m = list(csv.DictReader(f))
    lines += ["", "Performance measurements (seconds):", "", "| NFR | action | average | slowest |", "|---|---|---|---|"]
    for nfr in dict.fromkeys(r["nfr_id"] for r in m):
        t = [float(r["seconds"]) for r in m if r["nfr_id"] == nfr]
        lines.append(f"| {nfr} | {next(r['action'] for r in m if r['nfr_id'] == nfr)} | {sum(t) / len(t):.2f} | {max(t):.2f} |")
lines += ["", END]

report = os.path.join(HERE, "REPORT_SECTION.md")
text = open(report, encoding="utf-8").read()
table = "\n".join(lines)
if START in text:
    text = text[:text.index(START)] + table + text[text.index(END) + len(END):]
else:
    text = text.replace("RESULTS_TABLE", table)
open(report, "w", encoding="utf-8").write(text)
print(table)
