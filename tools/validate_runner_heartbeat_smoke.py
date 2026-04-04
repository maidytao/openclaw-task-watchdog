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
HEARTBEAT_RESULT_PATH = ROOT / "tasks" / "heartbeat-scheduler-observation-result.json"
SMOKE_RESULT_PATH = ROOT / "tasks" / "runner-heartbeat-smoke-result.json"
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


def run(args, use_cmd=False):
    command = ["cmd", "/c"] + args if use_cmd else args
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def seed_case():
    next_update_by = now_local()
    queue = [
        {
            "taskId": "runner-heartbeat-smoke-check",
            "status": "执行中",
            "message": {
                "status": "执行中",
                "deliverable": "验证 runner + heartbeat 端到端闭环",
                "blocker": "",
                "nextAction": "runner 产出 inbox，heartbeat 自动消费并收口",
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
    for path in [INBOX_PATH, BRIDGE_PATH, POLL_RESULT_PATH, HEARTBEAT_RESULT_PATH, REQUEST_PATH]:
        if path.exists():
            path.unlink()


def main():
    seed_case()
    steps = []
    steps.append(run(["tasks\\report-delivery-runner.bat"], use_cmd=True))
    steps.append(run(["python", "tools\\heartbeat_scheduler_observation.py"]))
    steps.append(run(["python", "tools\\heartbeat_scheduler_observation.py"]))

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    inbox = load_json(INBOX_PATH, {}) or {}
    bridge = load_json(BRIDGE_PATH, {}) or {}
    observations = load_json(OBS_PATH, []) or []
    heartbeat_result = load_json(HEARTBEAT_RESULT_PATH, {}) or {}
    poll_result = load_json(POLL_RESULT_PATH, {}) or {}
    attempts = state.get("toolDeliveryAttempts") or []

    result = {
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "attemptCount": len(attempts),
        "successAttemptCount": len([a for a in attempts if a.get("status") == "success"]),
        "pendingAttemptCount": len([a for a in attempts if a.get("status") == "pending_confirmation"]),
        "lastAttemptStatus": attempts[-1].get("status", "") if attempts else "",
        "observationCount": len(observations),
        "dispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "finalInboxStatus": inbox.get("status", ""),
        "finalBridgeReady": bridge.get("ready", False),
        "firstHeartbeatAction": json.loads(steps[1]["stdout"]).get("action", "") if steps[1].get("stdout") else "",
        "secondHeartbeatAction": heartbeat_result.get("action", ""),
        "pollResultOk": poll_result.get("ok", None),
    }
    result["closed"] = result["queueLength"] == 0 and not result["hasPendingToolPayload"] and not result["hasPendingConfirmation"] and result["lastError"] == "" and result["successAttemptCount"] == 1 and result["pendingAttemptCount"] == 1 and result["lastAttemptStatus"] == "success" and result["observationCount"] == 1 and result["dispatchRequestStatus"] == "reconciled_success" and result["firstHeartbeatAction"] == "polled" and result["secondHeartbeatAction"] == "idle"

    save_json(SMOKE_RESULT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
