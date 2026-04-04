import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
INBOX_PATH = ROOT / "tasks" / "scheduler-observation-inbox.json"
POLL_RESULT_PATH = ROOT / "tasks" / "scheduler-observation-poll-result.json"
OUT_PATH = ROOT / "tasks" / "heartbeat-scheduler-observation-result.json"
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
    inbox = load_json(INBOX_PATH, {}) or {}
    ready = bool(inbox.get("ready") and inbox.get("messageKey") and inbox.get("status") != "consumed")

    if not ready:
        result = {
            "checkedAt": now_local(),
            "ok": True,
            "action": "idle",
            "reason": "no_ready_scheduler_observation_inbox",
            "inboxStatus": inbox.get("status", ""),
            "messageKey": inbox.get("messageKey", ""),
        }
        save_json(OUT_PATH, result)
        payload = json.dumps(result, ensure_ascii=False)
        sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        return 0

    poll = run(["python", "tools\\poll_scheduler_observation_inbox.py"])
    poll_result = load_json(POLL_RESULT_PATH, {}) or {}
    result = {
        "checkedAt": now_local(),
        "ok": poll.get("returncode") == 0,
        "action": "polled",
        "messageKey": inbox.get("messageKey", ""),
        "poll": poll,
        "pollResult": poll_result,
    }
    save_json(OUT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
