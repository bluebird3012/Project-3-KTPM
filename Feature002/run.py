import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNNERS = {
    "Level1": ("Feature002_Level1/main.py",),
    "Level2": ("Feature002_Level2/main.py",),
    "NonFunctional": ("-m", "Feature002_NonFunctional.main"),
}
CREDENTIAL_KEYS = {"MOODLE_ADMIN_USERNAME", "MOODLE_ADMIN_PASSWORD"}


def main():
    parser = argparse.ArgumentParser(description="Run Moodle tests with credentials from .env.")
    parser.add_argument("suite", choices=RUNNERS)
    parser.add_argument("runner_args", nargs=argparse.REMAINDER, help="Arguments for the selected runner")
    args = parser.parse_args()

    environment = os.environ.copy()
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8-sig").split("\n"):
            key, _, value = line.partition("=")
            key = key.strip()
            if key in CREDENTIAL_KEYS and value:
                environment.setdefault(key, value)

    return subprocess.run(
        [sys.executable, "-B", *RUNNERS[args.suite], *args.runner_args],
        cwd=ROOT,
        env=environment,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
