#!/usr/bin/env python3
"""Run every public reproduction entry point and the offline release validator."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
COMMANDS = (
    ("continuation", ["run_continuation_suite.py"]),
    ("real_history", ["run_real_history_suite.py"]),
    ("cold_query", ["run_suite.py"]),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-dir", type=Path, default=None)
    parser.add_argument("--project-root", type=Path, default=None)
    args = parser.parse_args()
    start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    records = []
    error = None
    try:
        for name, parts in COMMANDS:
            wall = time.monotonic()
            process = subprocess.run(
                [sys.executable, *parts], cwd=ROOT, check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"},
            )
            records.append({"name": name, "command": ["python", *parts],
                            "exit_code": process.returncode, "wall_seconds": time.monotonic() - wall})
            if process.returncode:
                raise RuntimeError(f"{name} failed")
        wall = time.monotonic()
        process = subprocess.run(
            [sys.executable, "refresh_resource_ledger.py"], cwd=ROOT, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"},
        )
        records.append({"name": "resource_ledger", "command": ["python", "refresh_resource_ledger.py"],
                        "exit_code": process.returncode, "wall_seconds": time.monotonic() - wall})
        if process.returncode:
            raise RuntimeError("resource ledger refresh failed")
        validate = [sys.executable, "validate_release.py"]
        if args.paper_dir is not None:
            validate += ["--paper-dir", str(args.paper_dir)]
        if args.project_root is not None:
            validate += ["--project-root", str(args.project_root)]
        wall = time.monotonic()
        process = subprocess.run(validate, cwd=ROOT, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"})
        records.append({"name": "release_validation", "command": ["python", *validate[1:]],
                        "exit_code": process.returncode, "wall_seconds": time.monotonic() - wall})
        if process.returncode:
            raise RuntimeError("release validation failed")
    except RuntimeError as exc:
        error = str(exc)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {
        "status": "PASS" if error is None else "FAIL",
        "meaning": "sequential execution of all three public suites plus offline packet validation",
        "records": records,
        "error": error,
        "wall_seconds": time.monotonic() - start,
        "child_cpu_seconds": (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
        "maximum_child_rss_kib": after.ru_maxrss,
        "bounds": {"suites_sequential": True, "maximum_internal_trace_workers": 3},
    }
    (ROOT / "results/all-clean-reproduction.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    if error is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
