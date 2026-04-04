import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
OUT_PATH = ROOT / "tasks" / "report-delivery-suite-result.json"
COMPONENT_RESULTS = {
    "runner_inbox_stability": ROOT / "tasks" / "runner-inbox-stability-result.json",
    "heartbeat_scheduler_observation": ROOT / "tasks" / "heartbeat-scheduler-observation-validate-result.json",
    "runner_heartbeat_smoke": ROOT / "tasks" / "runner-heartbeat-smoke-result.json",
}
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
    steps = []
    steps.append({
        "name": "runner_inbox_stability",
        "run": run(["python", "tools\\validate_runner_inbox_stability.py"]),
    })
    steps.append({
        "name": "heartbeat_scheduler_observation",
        "run": run(["python", "tools\\validate_heartbeat_scheduler_observation.py"]),
    })
    steps.append({
        "name": "runner_heartbeat_smoke",
        "run": run(["python", "tools\\validate_runner_heartbeat_smoke.py"]),
    })

    components = {}
    all_closed = True
    for step in steps:
        name = step["name"]
        result = load_json(COMPONENT_RESULTS[name], {}) or {}
        closed = bool(result.get("closed"))
        all_closed = all_closed and closed and step["run"].get("returncode") == 0
        components[name] = {
            "closed": closed,
            "returncode": step["run"].get("returncode"),
            "resultPath": str(COMPONENT_RESULTS[name]),
            "summary": {
                "queueLength": result.get("queueLength"),
                "lastError": result.get("lastError"),
                "lastAttemptStatus": result.get("lastAttemptStatus"),
                "dispatchRequestStatus": result.get("dispatchRequestStatus"),
            },
        }

    suite = {
        "checkedAt": now_local(),
        "ok": all_closed,
        "components": components,
        "steps": steps,
    }
    save_json(OUT_PATH, suite)
    payload = json.dumps(suite, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
