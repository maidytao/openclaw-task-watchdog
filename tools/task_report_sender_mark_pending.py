import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
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
    payload = state.get("pendingToolPayload") or {}
    attempts = list(state.get("toolDeliveryAttempts", []) or [])

    message_key = payload.get("messageKey")
    if not message_key:
        print(json.dumps({
            "recorded": False,
            "reason": "no pendingToolPayload",
            "hasPendingConfirmation": "pendingConfirmation" in state,
        }, ensure_ascii=False))
        return 0

    existing_pending = state.get("pendingConfirmation") or {}
    if existing_pending.get("messageKey") == message_key:
        print(json.dumps({
            "recorded": False,
            "reason": "pending_confirmation_already_exists",
            "messageKey": message_key,
            "hasPendingConfirmation": True,
            "attemptCount": len(attempts),
        }, ensure_ascii=False))
        return 0

    for attempt in reversed(attempts):
        if attempt.get("messageKey") != message_key:
            continue
        if attempt.get("status") in {"success", "dispatched", "timeout_pending_confirmation", "pending_confirmation"}:
            print(json.dumps({
                "recorded": False,
                "reason": "delivery_attempt_already_recorded",
                "messageKey": message_key,
                "existingStatus": attempt.get("status"),
                "hasPendingConfirmation": "pendingConfirmation" in state,
                "attemptCount": len(attempts),
            }, ensure_ascii=False))
            return 0

    pending = {
        "recordedAt": now_local(),
        "sessionKey": payload.get("sessionKey", "current"),
        "messageKey": message_key,
        "note": "runner marked pending confirmation from sender payload"
    }
    state["pendingConfirmation"] = pending
    state["lastError"] = "pending confirmation after sessions_send timeout"

    attempts.append({
        "attemptedAt": pending["recordedAt"],
        "sessionKey": pending["sessionKey"],
        "messageKey": message_key,
        "messagePreview": (payload.get("message") or "")[:200],
        "status": "pending_confirmation",
        "note": pending["note"],
    })
    state["toolDeliveryAttempts"] = attempts[-20:]
    state["lastToolDeliveryAttemptAt"] = pending["recordedAt"]

    save_json(STATE_PATH, state)
    print(json.dumps({
        "recorded": True,
        "messageKey": message_key,
        "hasPendingConfirmation": True,
        "attemptCount": len(state["toolDeliveryAttempts"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
