import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
TASKS = ROOT / "tasks"
TZ = timezone(timedelta(hours=8))

PATHS = {
    "state": TASKS / "report-sender-state.json",
    "queue": TASKS / "report-queue.json",
    "dispatchRequest": TASKS / "report-dispatch-request.json",
    "inbox": TASKS / "scheduler-observation-inbox.json",
    "bridge": TASKS / "scheduler-observation-bridge.json",
    "pollResult": TASKS / "scheduler-observation-poll-result.json",
    "heartbeatResult": TASKS / "heartbeat-scheduler-observation-result.json",
    "suite": TASKS / "report-delivery-suite-result.json",
    "runnerStability": TASKS / "runner-inbox-stability-result.json",
    "heartbeatValidate": TASKS / "heartbeat-scheduler-observation-validate-result.json",
    "smoke": TASKS / "runner-heartbeat-smoke-result.json",
    "observations": TASKS / "report-delivery-observations.json",
}


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


def summarize_component(data):
    data = data or {}
    return {
        "ok": data.get("ok", data.get("closed", False)),
        "closed": data.get("closed", False),
        "queueLength": data.get("queueLength"),
        "lastError": data.get("lastError"),
        "lastAttemptStatus": data.get("lastAttemptStatus"),
        "dispatchRequestStatus": data.get("dispatchRequestStatus"),
    }


def main():
    state = load_json(PATHS["state"], {}) or {}
    queue = load_json(PATHS["queue"], []) or []
    dispatch = load_json(PATHS["dispatchRequest"], {}) or {}
    inbox = load_json(PATHS["inbox"], {}) or {}
    bridge = load_json(PATHS["bridge"], {}) or {}
    poll_result = load_json(PATHS["pollResult"], {}) or {}
    heartbeat_result = load_json(PATHS["heartbeatResult"], {}) or {}
    suite = load_json(PATHS["suite"], {}) or {}
    runner_stability = load_json(PATHS["runnerStability"], {}) or {}
    heartbeat_validate = load_json(PATHS["heartbeatValidate"], {}) or {}
    smoke = load_json(PATHS["smoke"], {}) or {}
    observations = load_json(PATHS["observations"], []) or []

    attempts = state.get("toolDeliveryAttempts") or []
    pending_payload = state.get("pendingToolPayload") or {}
    pending_confirmation = state.get("pendingConfirmation") or {}

    result = {
        "checkedAt": now_local(),
        "systemHealthy": bool(suite.get("ok")) and not state.get("lastError") and len(queue) == 0 and not pending_payload and not pending_confirmation,
        "current": {
            "queueLength": len(queue),
            "hasPendingToolPayload": bool(pending_payload),
            "hasPendingConfirmation": bool(pending_confirmation),
            "lastError": state.get("lastError", ""),
            "lastRunAt": state.get("lastRunAt", ""),
            "lastSentAt": state.get("lastSentAt", ""),
            "lastAttemptStatus": attempts[-1].get("status", "") if attempts else "",
            "successAttemptCount": len([a for a in attempts if a.get("status") == "success"]),
            "pendingAttemptCount": len([a for a in attempts if a.get("status") == "pending_confirmation"]),
            "dispatchRequestStatus": dispatch.get("status", (state.get("dispatchRequest") or {}).get("status", "")),
            "inboxStatus": inbox.get("status", ""),
            "inboxReady": inbox.get("ready", False),
            "bridgeReady": bridge.get("ready", False),
            "observationCount": len(observations),
            "activeMessageKey": pending_confirmation.get("messageKey") or pending_payload.get("messageKey") or inbox.get("messageKey", ""),
        },
        "latestResults": {
            "heartbeat": heartbeat_result,
            "poll": poll_result,
        },
        "validationSuite": {
            "ok": suite.get("ok", False),
            "checkedAt": suite.get("checkedAt", ""),
            "components": {
                "runner_inbox_stability": summarize_component(runner_stability),
                "heartbeat_scheduler_observation": summarize_component(heartbeat_validate),
                "runner_heartbeat_smoke": summarize_component(smoke),
            },
        },
        "paths": {name: str(path) for name, path in PATHS.items()},
    }

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
