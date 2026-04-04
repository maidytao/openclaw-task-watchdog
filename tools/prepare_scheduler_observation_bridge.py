import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
OUT_PATH = ROOT / "tasks" / "scheduler-observation-bridge.json"
INBOX_PATH = ROOT / "tasks" / "scheduler-observation-inbox.json"
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


def main():
    state = load_json(STATE_PATH, {}) or {}
    pending = state.get("pendingConfirmation") or {}
    payload = state.get("pendingToolPayload") or {}
    message_key = pending.get("messageKey") or payload.get("messageKey") or ""

    result = {
        "preparedAt": now_local(),
        "kind": "scheduler_observation_bridge",
        "ready": bool(message_key),
        "messageKey": message_key,
        "sessionKey": pending.get("sessionKey") or payload.get("sessionKey") or "current",
        "message": payload.get("message", ""),
        "nextAction": "observe delivered chat message in current session, then write success observation and run reconcile",
        "commands": [
            "python tools\\task_report_sender_confirm_success.py --source scheduled_task_observed --note \"scheduled task delivery observed in current chat\"",
            "python tools\\task_report_sender_reconcile.py --note \"reconcile after scheduled task observed delivery\"",
            "python tools\\cleanup_stale_report_protocol.py"
        ]
    }
    inbox = {
        "createdAt": result["preparedAt"],
        "kind": "scheduler_observation_inbox",
        "ready": result["ready"],
        "status": "ready" if result["ready"] else "idle",
        "messageKey": result["messageKey"],
        "sessionKey": result["sessionKey"],
        "bridgePath": str(OUT_PATH),
        "consumeWith": "python tools\\poll_scheduler_observation_inbox.py",
    }
    save_json(OUT_PATH, result)
    save_json(INBOX_PATH, inbox)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
