import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
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
    if not payload:
        if REQUEST_PATH.exists():
            REQUEST_PATH.unlink()
        print(json.dumps({
            "planned": False,
            "reason": "no pendingToolPayload",
            "requestPath": str(REQUEST_PATH),
        }, ensure_ascii=False))
        return 0

    message_key = payload.get("messageKey", "")
    existing = load_json(REQUEST_PATH, {}) or {}
    dispatch = state.get("dispatchRequest") or {}
    if dispatch.get("messageKey") == message_key and dispatch.get("status") in {
        "ready", "claimed", "dispatched", "timeout_pending_confirmation", "observed_success", "reconciled_success"
    }:
        if not REQUEST_PATH.exists() and existing:
            save_json(REQUEST_PATH, existing)
        print(json.dumps({
            "planned": False,
            "reason": "dispatch_request_already_active",
            "requestPath": str(REQUEST_PATH),
            "messageKey": message_key,
            "status": dispatch.get("status"),
            "attemptCount": dispatch.get("attemptCount", 0),
        }, ensure_ascii=False))
        return 0

    request = {
        "createdAt": now_local(),
        "sessionKey": payload.get("sessionKey", "current"),
        "message": payload.get("message", ""),
        "messageKey": message_key,
        "taskId": payload.get("taskId", ""),
        "source": "pendingToolPayload",
        "status": "ready",
        "attemptCount": int(existing.get("attemptCount", 0)) + 1 if existing.get("messageKey") == payload.get("messageKey") else 1,
    }
    save_json(REQUEST_PATH, request)

    state["dispatchRequest"] = {
        "plannedAt": request["createdAt"],
        "requestPath": str(REQUEST_PATH),
        "messageKey": request["messageKey"],
        "status": request["status"],
        "attemptCount": request["attemptCount"],
    }
    save_json(STATE_PATH, state)

    print(json.dumps({
        "planned": True,
        "requestPath": str(REQUEST_PATH),
        "messageKey": request["messageKey"],
        "attemptCount": request["attemptCount"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
