import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
HANDOFF_PATH = ROOT / "tasks" / "report-live-dispatch-handoff.json"
PLAN_PATH = ROOT / "tasks" / "report-live-send-plan.json"
RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"
OUT_PATH = ROOT / "tasks" / "report-protocol-cleanup-result.json"
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


def last_success_attempt(state):
    for attempt in reversed(list(state.get("toolDeliveryAttempts", []) or [])):
        if attempt.get("status") == "success":
            return attempt
    return {}


def normalize(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def main():
    state = load_json(STATE_PATH, {}) or {}
    success = last_success_attempt(state)
    if not success or state.get("lastError"):
        result = {"ok": False, "reason": "no_clean_success_terminal_state"}
        save_json(OUT_PATH, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    success_key = normalize(success.get("messageKey"))
    terminal_at = success.get("attemptedAt") or state.get("lastSentAt") or now_local()
    terminal_note = success.get("note") or "cleanup stale protocol after success"

    removed = []
    kept = []

    dispatch_state = state.get("dispatchRequest") or {}
    if normalize(dispatch_state.get("messageKey")) == success_key:
        dispatch_state["status"] = "reconciled_success"
        dispatch_state["reconciledAt"] = terminal_at
        dispatch_state["result"] = {
            "status": "reconciled_success",
            "recordedAt": terminal_at,
            "note": terminal_note,
        }
        state["dispatchRequest"] = dispatch_state
    else:
        state.pop("dispatchRequest", None)

    live_plan_state = state.get("liveSendPlan") or {}
    if normalize(live_plan_state.get("messageKey")) == success_key:
        live_plan_state["status"] = "reconciled_success"
        live_plan_state["reconciledAt"] = terminal_at
        live_plan_state["result"] = {
            "status": "reconciled_success",
            "recordedAt": terminal_at,
            "note": terminal_note,
        }
        state["liveSendPlan"] = live_plan_state
    else:
        state.pop("liveSendPlan", None)

    for path in [REQUEST_PATH, HANDOFF_PATH, PLAN_PATH]:
        data = load_json(path, {}) or {}
        if data and normalize(data.get("messageKey")) == success_key:
            data["status"] = "reconciled_success"
            data["reconciledAt"] = terminal_at
            data["result"] = {
                "status": "reconciled_success",
                "recordedAt": terminal_at,
                "note": terminal_note,
            }
            save_json(path, data)
            kept.append(str(path))
        elif path.exists():
            path.unlink()
            removed.append(str(path))

    live_result = load_json(RESULT_PATH, {}) or {}
    if live_result:
        live_result["status"] = "reconciled_success"
        live_result["reconciledAt"] = terminal_at
        live_result["note"] = terminal_note
        save_json(RESULT_PATH, live_result)
        kept.append(str(RESULT_PATH))

    save_json(STATE_PATH, state)

    result = {
        "ok": True,
        "successMessageKey": success_key,
        "terminalAt": terminal_at,
        "removed": removed,
        "kept": kept,
        "stateDispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "stateLiveSendPlanStatus": (state.get("liveSendPlan") or {}).get("status", ""),
    }
    save_json(OUT_PATH, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
