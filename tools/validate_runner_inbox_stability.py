import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
QUEUE_PATH = ROOT / "tasks" / "report-queue.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
INBOX_PATH = ROOT / "tasks" / "scheduler-observation-inbox.json"
BRIDGE_PATH = ROOT / "tasks" / "scheduler-observation-bridge.json"
POLL_RESULT_PATH = ROOT / "tasks" / "scheduler-observation-poll-result.json"
RESULT_PATH = ROOT / "tasks" / "runner-inbox-stability-result.json"
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


def seed_case():
    next_update_by = now_local()
    queue = [
        {
            "taskId": "runner-inbox-check",
            "status": "执行中",
            "message": {
                "status": "执行中",
                "deliverable": "验证 runner 自动产出 inbox 且多轮不重入",
                "blocker": "",
                "nextAction": "runner 产出 observation inbox，poller 自动消费",
                "nextUpdateBy": next_update_by,
            },
        }
    ]
    state = {
        "lastRunAt": "",
        "lastSentAt": "",
        "sentKeys": [],
        "delivered": [],
        "lastError": "",
        "lastProcessedCount": 0,
        "toolDeliveryAttempts": [],
        "lastToolDeliveryAttemptAt": "",
        "refreshedItems": [],
    }
    save_json(QUEUE_PATH, queue)
    save_json(STATE_PATH, state)
    save_json(OBS_PATH, [])
    for path in [INBOX_PATH, BRIDGE_PATH, POLL_RESULT_PATH, ROOT / "tasks" / "report-dispatch-request.json"]:
        if path.exists():
            path.unlink()


def main():
    seed_case()
    steps = []
    steps.append(run(["cmd", "/c", "tasks\\report-delivery-runner.bat"]))
    steps.append(run(["python", "tools\\poll_scheduler_observation_inbox.py"]))
    steps.append(run(["cmd", "/c", "tasks\\report-delivery-runner.bat"]))
    steps.append(run(["python", "tools\\poll_scheduler_observation_inbox.py"]))
    steps.append(run(["cmd", "/c", "tasks\\report-delivery-runner.bat"]))

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    inbox = load_json(INBOX_PATH, {}) or {}
    bridge = load_json(BRIDGE_PATH, {}) or {}
    poll_result = load_json(POLL_RESULT_PATH, {}) or {}
    observations = load_json(OBS_PATH, []) or []
    attempts = state.get("toolDeliveryAttempts") or []
    success_attempts = [a for a in attempts if a.get("status") == "success"]
    pending_attempts = [a for a in attempts if a.get("status") == "pending_confirmation"]
    first_poll_ok = bool(((steps[1] or {}).get("returncode") == 0) and (poll_result.get("ok") is False or poll_result.get("ok") is True))
    first_consumption_happened = any("consume_scheduler_observation_bridge.py" in ((step.get("stdout") or "")) for step in steps[:2])

    result = {
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "attemptCount": len(attempts),
        "successAttemptCount": len(success_attempts),
        "pendingAttemptCount": len(pending_attempts),
        "lastAttemptStatus": attempts[-1].get("status", "") if attempts else "",
        "observationCount": len(observations),
        "dispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "finalInboxStatus": inbox.get("status", ""),
        "finalBridgeReady": bridge.get("ready", False),
        "pollResultOk": poll_result.get("ok", None),
        "firstPollRan": first_poll_ok,
        "firstConsumptionHappened": first_consumption_happened,
        "stable": len(queue) == 0 and "pendingToolPayload" not in state and "pendingConfirmation" not in state and state.get("lastError", "") == "" and len(success_attempts) == 1 and len(pending_attempts) == 1 and (state.get("dispatchRequest") or {}).get("status", "") == "reconciled_success" and first_consumption_happened,
    }
    result["closed"] = result["stable"]
    save_json(RESULT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
