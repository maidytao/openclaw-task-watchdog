import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
INBOX_PATH = ROOT / "tasks" / "scheduler-observation-inbox.json"
BRIDGE_PATH = ROOT / "tasks" / "scheduler-observation-bridge.json"
OUT_PATH = ROOT / "tasks" / "scheduler-observation-poll-result.json"
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
    bridge = load_json(BRIDGE_PATH, {}) or {}
    inbox_key = inbox.get("messageKey", "")
    bridge_key = bridge.get("messageKey", "")

    if not inbox.get("ready") or not inbox_key or inbox.get("status") == "consumed":
        result = {
            "checkedAt": now_local(),
            "ok": False,
            "reason": "no_ready_inbox_item",
            "inboxStatus": inbox.get("status", ""),
            "messageKey": inbox_key,
        }
        save_json(OUT_PATH, result)
        payload = json.dumps(result, ensure_ascii=False)
        sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        return 0

    if bridge_key and bridge_key != inbox_key:
        result = {
            "checkedAt": now_local(),
            "ok": False,
            "reason": "bridge_inbox_message_key_mismatch",
            "inboxMessageKey": inbox_key,
            "bridgeMessageKey": bridge_key,
        }
        save_json(OUT_PATH, result)
        payload = json.dumps(result, ensure_ascii=False)
        sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        return 0

    consume = run(["python", "tools\\consume_scheduler_observation_bridge.py"])
    inbox = load_json(INBOX_PATH, {}) or {}
    inbox["status"] = "consumed" if consume.get("returncode") == 0 else "consume_failed"
    inbox["consumedAt"] = now_local()
    inbox["consumeResultPath"] = str(ROOT / "tasks" / "scheduler-observation-consume-result.json")
    save_json(INBOX_PATH, inbox)

    result = {
        "checkedAt": now_local(),
        "ok": consume.get("returncode") == 0,
        "messageKey": inbox_key,
        "consume": consume,
        "inboxStatus": inbox.get("status", ""),
    }
    save_json(OUT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
