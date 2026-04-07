import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
HANDOFF_PATH = ROOT / "tasks" / "report-live-dispatch-handoff.json"
PLAN_PATH = ROOT / "tasks" / "report-live-send-plan.json"
RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"
SYNC_RESULT_PATH = ROOT / "tasks" / "report-terminal-sync-result.json"
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


def message_key_from_last_delivered(value: str):
    if not value:
        return ""
    parts = str(value).split("|", 2)
    if len(parts) < 3:
        return ""
    return parts[1]


def latest_success_attempt(attempts):
    for attempt in reversed(attempts or []):
        if attempt.get("status") == "success":
            return attempt
    return {}


def latest_pending_attempt(attempts):
    for attempt in reversed(attempts or []):
        if attempt.get("status") == "pending_confirmation":
            return attempt
    return {}


def main():
    state = load_json(STATE_PATH, {}) or {}
    request = load_json(REQUEST_PATH, {}) or {}
    handoff = load_json(HANDOFF_PATH, {}) or {}
    plan = load_json(PLAN_PATH, {}) or {}
    live_result = load_json(RESULT_PATH, {}) or {}

    last_delivered_key = message_key_from_last_delivered(state.get("lastDeliveredPayloadKey", ""))
    attempts = state.get("toolDeliveryAttempts") or []
    success = latest_success_attempt(attempts)
    pending = latest_pending_attempt(attempts)
    success_key = success.get("messageKey", "")
    pending_key = pending.get("messageKey", "")
    target_key = success_key or pending_key or last_delivered_key

    changed = {
        "state": False,
        "request": False,
        "handoff": False,
        "plan": False,
        "result": False,
    }

    pending_only = bool(target_key and not success_key and pending_key)

    if not target_key:
        result = {
            "ok": False,
            "reason": "no_success_terminal_state",
            "targetMessageKey": target_key,
            "lastError": state.get("lastError", ""),
        }
        save_json(SYNC_RESULT_PATH, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    terminal_time = success.get("attemptedAt") or pending.get("attemptedAt") or state.get("lastSentAt") or now_local()
    terminal_note = success.get("note") or pending.get("note") or "synced from sender terminal state"
    target_status = "reconciled_success" if success_key else "pending_confirmation"

    dispatch_state = state.get("dispatchRequest") or {}
    if dispatch_state.get("messageKey") == target_key:
        dispatch_state["status"] = target_status
        dispatch_state["reconciledAt"] = terminal_time
        dispatch_state["result"] = {
            "status": target_status,
            "recordedAt": terminal_time,
            "note": terminal_note,
        }
        state["dispatchRequest"] = dispatch_state
        changed["state"] = True

    if request.get("messageKey") == target_key:
        request["status"] = target_status
        request["reconciledAt"] = terminal_time
        request["result"] = {
            "status": target_status,
            "recordedAt": terminal_time,
            "note": terminal_note,
        }
        save_json(REQUEST_PATH, request)
        changed["request"] = True

    if handoff.get("messageKey") == target_key:
        handoff["status"] = target_status
        handoff["reconciledAt"] = terminal_time
        handoff["result"] = {
            "status": target_status,
            "recordedAt": terminal_time,
            "note": terminal_note,
        }
        save_json(HANDOFF_PATH, handoff)
        changed["handoff"] = True

    if plan.get("messageKey") == target_key:
        plan["status"] = target_status
        plan["reconciledAt"] = terminal_time
        plan["result"] = {
            "status": target_status,
            "recordedAt": terminal_time,
            "note": terminal_note,
        }
        save_json(PLAN_PATH, plan)
        changed["plan"] = True

    if (state.get("liveSendPlan") or {}).get("messageKey") == target_key:
        live_plan_state = state.get("liveSendPlan") or {}
        live_plan_state["status"] = target_status
        live_plan_state["reconciledAt"] = terminal_time
        live_plan_state["result"] = {
            "status": target_status,
            "recordedAt": terminal_time,
            "note": terminal_note,
        }
        state["liveSendPlan"] = live_plan_state
        changed["state"] = True

    if live_result:
        live_result["status"] = target_status if pending_only else "reconciled_success"
        live_result["reconciledAt"] = terminal_time
        live_result["note"] = terminal_note
        save_json(RESULT_PATH, live_result)
        changed["result"] = True

    if changed["state"]:
        save_json(STATE_PATH, state)

    result = {
        "ok": True,
        "targetMessageKey": target_key,
        "mode": "pending_confirmation" if pending_only else "success",
        "terminalAt": terminal_time,
        "changed": changed,
        "dispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "liveSendPlanStatus": (state.get("liveSendPlan") or {}).get("status", ""),
        "requestStatus": request.get("status", "") if isinstance(request, dict) else "",
        "handoffStatus": handoff.get("status", "") if isinstance(handoff, dict) else "",
        "planStatus": plan.get("status", "") if isinstance(plan, dict) else "",
        "liveResultStatus": live_result.get("status", "") if isinstance(live_result, dict) else "",
    }
    save_json(SYNC_RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
