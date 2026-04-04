import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
QUEUE_PATH = ROOT / "tasks" / "report-queue.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
HANDOFF_PATH = ROOT / "tasks" / "report-live-dispatch-handoff.json"
PLAN_PATH = ROOT / "tasks" / "report-live-send-plan.json"
RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"
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


def parse_args():
    parser = argparse.ArgumentParser(description="Reconcile pending sender confirmations")
    parser.add_argument("--observed-success", action="store_true")
    parser.add_argument("--note", default="")
    return parser.parse_args()


def normalize_text(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def queue_message_key(item):
    msg = item.get("message") or {}
    return "|".join([
        normalize_text(item.get("taskId", "")),
        normalize_text(item.get("status", "")),
        normalize_text(msg.get("blocker", "")),
        normalize_text(msg.get("nextAction", "")),
        normalize_text(msg.get("nextUpdateBy", "")),
    ])


def filter_queue(queue, message_key):
    if not message_key:
        return queue
    filtered = []
    normalized_target = normalize_text(message_key)
    for item in queue:
        item_key = queue_message_key(item)
        if item_key != normalized_target:
            filtered.append(item)
    return filtered


def payload_key(payload):
    if not payload:
        return ""
    return "|".join([
        str(payload.get("sessionKey", "")),
        str(payload.get("messageKey", "")),
        str(payload.get("message", "")),
    ])


def observation_matches(observations, message_key):
    normalized_target = normalize_text(message_key)
    for item in observations or []:
        if normalize_text(item.get("messageKey")) == normalized_target and item.get("status") == "success":
            return item
    return None


def has_real_success_observation(observation):
    if not observation:
        return False
    source = str(observation.get("source", "")).strip().lower()
    note = str(observation.get("note", "")).strip().lower()
    if source and source not in {"synthetic", "runner_synthetic"}:
        return True
    if "runner-driven observation writer" in note:
        return False
    return bool(note)


def clear_protocol_artifacts(message_key, terminal_attempt):
    request = load_json(REQUEST_PATH, {}) or {}
    handoff = load_json(HANDOFF_PATH, {}) or {}
    plan = load_json(PLAN_PATH, {}) or {}
    result = load_json(RESULT_PATH, {}) or {}

    terminal_result = {
        "status": "reconciled_success",
        "recordedAt": terminal_attempt.get("attemptedAt", now_local()),
        "note": terminal_attempt.get("note", "reconciled to success"),
    }

    if request and normalize_text(request.get("messageKey")) == message_key:
        request["status"] = "reconciled_success"
        request["reconciledAt"] = terminal_result["recordedAt"]
        request["result"] = terminal_result
        save_json(REQUEST_PATH, request)
    elif REQUEST_PATH.exists():
        REQUEST_PATH.unlink()

    if handoff and normalize_text(handoff.get("messageKey")) == message_key:
        handoff["status"] = "reconciled_success"
        handoff["reconciledAt"] = terminal_result["recordedAt"]
        handoff["result"] = terminal_result
        save_json(HANDOFF_PATH, handoff)
    elif HANDOFF_PATH.exists():
        HANDOFF_PATH.unlink()

    if plan and normalize_text(plan.get("messageKey")) == message_key:
        plan["status"] = "reconciled_success"
        plan["reconciledAt"] = terminal_result["recordedAt"]
        plan["result"] = terminal_result
        save_json(PLAN_PATH, plan)
    elif PLAN_PATH.exists():
        PLAN_PATH.unlink()

    if result:
        result["status"] = "reconciled_success"
        result["reconciledAt"] = terminal_result["recordedAt"]
        result["note"] = terminal_result["note"]
        save_json(RESULT_PATH, result)


def main():
    args = parse_args()
    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    observations = load_json(OBS_PATH, []) or []
    pending = state.get("pendingConfirmation") or {}
    payload = state.get("pendingToolPayload") or {}
    attempts = list(state.get("toolDeliveryAttempts", []) or [])

    if not pending:
        print(json.dumps({
            "action": "noop",
            "reason": "no pendingConfirmation",
            "queueLength": len(queue),
        }, ensure_ascii=False))
        return 0

    message_key = normalize_text(pending.get("messageKey") or payload.get("messageKey"))
    matched_observation = observation_matches(observations, message_key)
    observed_success = bool(args.observed_success or has_real_success_observation(matched_observation))

    if observed_success:
        for attempt in reversed(attempts):
            if normalize_text(attempt.get("messageKey")) != message_key:
                continue
            if attempt.get("status") == "success":
                state.pop("pendingToolPayload", None)
                state.pop("pendingConfirmation", None)
                state["lastError"] = ""
                queue = filter_queue(queue, message_key)
                clear_protocol_artifacts(message_key, attempt)
                save_json(STATE_PATH, state)
                save_json(QUEUE_PATH, queue)
                print(json.dumps({
                    "action": "already_reconciled_success",
                    "queueLength": len(queue),
                    "hasPendingConfirmation": "pendingConfirmation" in state,
                    "hasPendingToolPayload": "pendingToolPayload" in state,
                    "lastError": state.get("lastError", ""),
                    "matchedObservation": matched_observation,
                }, ensure_ascii=False))
                return 0

        attempt = {
            "attemptedAt": now_local(),
            "sessionKey": pending.get("sessionKey") or payload.get("sessionKey"),
            "messageKey": message_key,
            "messagePreview": (payload.get("message") or "")[:200],
            "status": "success",
            "note": args.note or (
                f"reconciled from real observation file: {matched_observation.get('note', '')}" if matched_observation else "reconciled from pending confirmation after observed success"
            ),
        }
        attempts.append(attempt)
        state["toolDeliveryAttempts"] = attempts[-20:]
        state["lastToolDeliveryAttemptAt"] = attempt["attemptedAt"]
        state["lastSentAt"] = attempt["attemptedAt"]
        state["lastDeliveredPayloadKey"] = payload_key(payload)
        state["lastError"] = ""
        queue = filter_queue(queue, message_key)
        state.pop("pendingToolPayload", None)
        state.pop("pendingConfirmation", None)
        clear_protocol_artifacts(message_key, attempt)
        action = "reconciled_to_success"
    else:
        for attempt in reversed(attempts):
            if normalize_text(attempt.get("messageKey")) != message_key:
                continue
            if attempt.get("status") == "pending_confirmation":
                save_json(STATE_PATH, state)
                save_json(QUEUE_PATH, queue)
                print(json.dumps({
                    "action": "already_pending",
                    "queueLength": len(queue),
                    "hasPendingConfirmation": "pendingConfirmation" in state,
                    "hasPendingToolPayload": "pendingToolPayload" in state,
                    "lastError": state.get("lastError", ""),
                    "matchedObservation": matched_observation,
                }, ensure_ascii=False))
                return 0

        attempt = {
            "attemptedAt": now_local(),
            "sessionKey": pending.get("sessionKey") or payload.get("sessionKey"),
            "messageKey": message_key,
            "messagePreview": (payload.get("message") or "")[:200],
            "status": "pending_confirmation",
            "note": args.note or "pending confirmation still awaiting observation",
        }
        attempts.append(attempt)
        state["toolDeliveryAttempts"] = attempts[-20:]
        state["lastToolDeliveryAttemptAt"] = attempt["attemptedAt"]
        state["lastError"] = "pending confirmation after sessions_send timeout"
        action = "kept_pending"

    save_json(STATE_PATH, state)
    save_json(QUEUE_PATH, queue)

    print(json.dumps({
        "action": action,
        "queueLength": len(queue),
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "lastError": state.get("lastError", ""),
        "matchedObservation": matched_observation,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
