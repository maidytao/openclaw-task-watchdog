import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
OUT_PATH = ROOT / "tasks" / "report-delivery-acceptance-result.json"
SUITE_PATH = ROOT / "tasks" / "report-delivery-suite-result.json"
TZ = timezone(timedelta(hours=8))


def now_local():
    return datetime.now(TZ).isoformat()


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return default
    if not raw or not raw.strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    suite_run = run(["python", "tools\\validate_report_delivery_suite.py"])
    status_run = run(["python", "tools\\report_delivery_status.py"])

    suite = load_json(SUITE_PATH, {}) or {}
    try:
        status = json.loads(status_run.get("stdout") or "{}")
    except json.JSONDecodeError:
        status = {}

    suite_ok = bool(suite.get("ok")) and suite_run.get("returncode") == 0
    status_ok = bool(status.get("systemHealthy")) and status_run.get("returncode") == 0
    passed = suite_ok and status_ok

    failures = []
    if not suite_ok:
        failures.append("validation_suite_failed")
    if not status_ok:
        failures.append("status_not_healthy")

    result = {
        "checkedAt": now_local(),
        "passed": passed,
        "verdict": "PASS" if passed else "FAIL",
        "failures": failures,
        "suite": {
            "ok": suite.get("ok", False),
            "checkedAt": suite.get("checkedAt", ""),
            "path": str(SUITE_PATH),
        },
        "status": {
            "systemHealthy": status.get("systemHealthy", False),
            "queueLength": ((status.get("current") or {}).get("queueLength")),
            "lastError": ((status.get("current") or {}).get("lastError")),
            "lastAttemptStatus": ((status.get("current") or {}).get("lastAttemptStatus")),
            "dispatchRequestStatus": ((status.get("current") or {}).get("dispatchRequestStatus")),
        },
        "paths": (status.get("paths") or {}),
        "steps": [
            {"name": "suite", "run": suite_run},
            {"name": "status", "run": status_run},
        ],
    }

    save_json(OUT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
