"""Safe Moodle Quiz cleanup tool for Feature 004 (dry-run by default).

Deletes ONLY test quizzes in the configured course (default course=2) via
Moodle's official `course_delete_module($cmid)` API executed inside the local
Moodle web container (`docker exec -i <container> php -r ...`).

Modes:
  1. Clean quizzes recorded in a specific run directory's cleanup_candidates.csv / all_results.csv:
       python cleanup.py results/run_... [--apply]
  2. Clean all Feature 004 test quizzes in course=2 matching test naming pattern (`f4_*`, `Q`, `Q7`):
       python cleanup.py --by-prefix [--apply]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from core.config import ROOT_DIR, get_course_id, load_local_env

PHP_BRIDGE = r"""
define('CLI_SCRIPT', true);
$input = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$candidates = !empty($input['config']) ? [$input['config']] : [
    '/var/www/site/moodle/config.php',
    '/var/www/html/config.php',
    '/var/www/moodle/config.php',
];
$cfg = null;
foreach ($candidates as $p) {
    if (is_file($p)) { $cfg = $p; break; }
}
if (!$cfg) { throw new RuntimeException('Moodle config.php not found'); }
require $cfg;
require_once($CFG->dirroot . '/course/lib.php');

$courseid = (int)$input['course_id'];
$quizmod = $DB->get_record('modules', ['name' => 'quiz'], 'id', MUST_EXIST);
$sql = "SELECT cm.id AS cmid, q.id AS quizid, q.name
          FROM {course_modules} cm
          JOIN {quiz} q ON q.id = cm.instance
         WHERE cm.course = ? AND cm.module = ? AND cm.deletioninprogress = 0
         ORDER BY cm.id ASC";
$rows = $DB->get_records_sql($sql, [$courseid, $quizmod->id]);

$target_cmids = array_map('intval', $input['cmids'] ?? []);
$by_prefix = !empty($input['by_prefix']);
$matched = [];
foreach ($rows as $r) {
    $is_test_name = (strpos($r->name, 'f4_') === 0 || $r->name === 'Q' || $r->name === 'Q7');
    $cmid = (int)$r->cmid;
    if (($by_prefix && $is_test_name) || (in_array($cmid, $target_cmids, true) && $is_test_name)) {
        $matched[] = ['cmid' => $cmid, 'quizid' => (int)$r->quizid, 'name' => mb_substr($r->name, 0, 80)];
    }
}

$deleted = [];
if (!empty($input['apply'])) {
    foreach ($matched as $item) {
        course_delete_module($item['cmid']);
        $deleted[] = $item;
    }
}
echo "\nCLEANUP_JSON:" . json_encode(['ok' => true, 'matched' => $matched, 'deleted' => $deleted], JSON_UNESCAPED_UNICODE) . "\n";
"""


def collect_cmids_from_run(run_dir: Path) -> list[int]:
    cmids: set[int] = set()
    for csv_path in list(run_dir.glob("all_results.csv")) + list(run_dir.rglob("cleanup_candidates.csv")):
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                raw = (row.get("created_cmid") or "").strip()
                if raw.isdigit():
                    cmids.add(int(raw))
    return sorted(cmids)


def run_bridge(container: str, payload: dict) -> dict:
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "php", "-r", PHP_BRIDGE],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
    )
    if proc.returncode != 0 or "CLEANUP_JSON:" not in proc.stdout:
        raise RuntimeError(
            "Moodle CLI cleanup bridge failed. Check Docker container name and Moodle config path.\n"
            + (proc.stderr or proc.stdout)[-800:]
        )
    line = proc.stdout.rsplit("CLEANUP_JSON:", 1)[1].splitlines()[0]
    return json.loads(line)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_local_env(ROOT_DIR / ".env")

    parser = argparse.ArgumentParser(description="Safe Moodle Quiz cleanup for Feature 004")
    parser.add_argument("run_directory", nargs="?", type=Path, help="Path to results/run_... directory")
    parser.add_argument("--by-prefix", action="store_true", help="Match all test quizzes (f4_*, Q, Q7) in course")
    parser.add_argument("--apply", action="store_true", help="Actually delete matched quizzes (default: dry-run)")
    args = parser.parse_args(argv)

    if not args.run_directory and not args.by_prefix:
        parser.error("Provide a run_directory or --by-prefix")

    container = os.environ.get("MOODLE_WEB_CONTAINER", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", container):
        raise ValueError("Set MOODLE_WEB_CONTAINER in .env (e.g. moodle-demo-webserver-1)")

    cmids: list[int] = []
    if args.run_directory:
        run_dir = args.run_directory.resolve()
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run directory not found: {run_dir}")
        cmids = collect_cmids_from_run(run_dir)

    payload = {
        "config": os.environ.get("MOODLE_CONFIG_PATH", ""),
        "course_id": get_course_id(),
        "cmids": cmids,
        "by_prefix": bool(args.by_prefix),
        "apply": bool(args.apply),
    }
    res = run_bridge(container, payload)
    matched = res["matched"]
    deleted = res["deleted"]
    print(f"Course {payload['course_id']} ({container}): matched={len(matched)} test quizzes.")
    for item in matched[:15]:
        print(f"  cmid={item['cmid']} | name={item['name']}")
    if len(matched) > 15:
        print(f"  ... (+{len(matched) - 15} more)")

    if not args.apply:
        print("Dry-run only. Re-run with --apply to delete matched test quizzes via Moodle course_delete_module().")
        return 0

    print(f"Deleted {len(deleted)} test quizzes via Moodle course_delete_module().")
    if args.run_directory:
        (args.run_directory / "cleanup_report.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
