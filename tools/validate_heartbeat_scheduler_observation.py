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
HEARTBEAT_RESULT_PATH = ROOT / "tasks" / "heartbeat-scheduler-observation-result.json"
VALIDATE_RESULT_PATH = ROOT / "tasks" / "heartbeat-scheduler-observation-validate-result.json"
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


def seed_pending_case():
    next_update_by = now_local()
    message_key = f"heartbeat-inbox-check|执行中||heartbeat 自动消费 scheduler observation inbox|{next_update_by}"
    queue = [
        {
            "taskId": "heartbeat-inbox-check",
            "status": "执行中",
            "message": {
                "status": "执行中",
                "deliverable": "验证 heartbeat 自动消费 scheduler observation inbox",
                "blocker": "",
                "nextAction": "heartbeat 自动消费 scheduler observation inbox",
                "nextUpdateBy": next_update_by,
            },
        }
    ]
    state = {
        "lastRunAt": now_local(),
        "lastSentAt": "",
        "sentKeys": [],
        "delivered": [],
        "lastError": "pending confirmation after sessions_send timeout",
        "lastProcessedCount": 0,
        "toolDeliveryAttempts": [
            {
                "attemptedAt": now_local(),
                "sessionKey": "current",
                "messageKey": message_key,
                "messagePreview": "[[reply_to_current]] 任务状态通知",
                "status": "pending_confirmation",
                "note": "seeded pending for heartbeat validation",
            }
        ],
        "lastToolDeliveryAttemptAt": now_local(),
        "refreshedItems": [],
        "pendingToolPayload": {
            "sessionKey": "current",
            "message": f"[[reply_to_current]] 任务状态通知\n状态：执行中\n交付物：验证 heartbeat 自动消费 scheduler observation inbox\n阻塞：\n下一步：heartbeat 自动消费 scheduler observation inbox\n下次更新：{next_update_by}",
            "messageKey": message_key,
            "taskId": "heartbeat-inbox-check",
            "createdAt": now_local(),
            "freshness": {"nextUpdateBy": next_update_by, "isExpired": False, "ageSeconds": 0},
        },
        "pendingConfirmation": {
            "recordedAt": now_local(),
            "sessionKey": "current",
            "messageKey": message_key,
            "note": "seeded pending for heartbeat validation",
        },
        "dispatchRequest": {
            "plannedAt": now_local(),
            "requestPath": str(ROOT / "tasks" / "report-dispatch-request.json"),
            "messageKey": message_key,
            "status": "ready",
            "attemptCount": 1,
        },
    }
    bridge = {
        "preparedAt": now_local(),
        "kind": "scheduler_observation_bridge",
        "ready": True,
        "messageKey": message_key,
        "sessionKey": "current",
        "message": state["pendingToolPayload"]["message"],
        "nextAction": "observe delivered chat message in current session, then write success observation and run reconcile",
        "commands": [
            "python tools\\task_report_sender_confirm_success.py --source scheduled_task_observed --note \"scheduled task delivery observed in current chat\"",
            "python tools\\task_report_sender_reconcile.py --note \"reconcile after scheduled task observed delivery\"",
            "python tools\\cleanup_stale_report_protocol.py",
        ],
    }
    inbox = {
        "createdAt": now_local(),
        "kind": "scheduler_observation_inbox",
        "ready": True,
        "status": "ready",
        "messageKey": message_key,
        "sessionKey": "current",
        "bridgePath": str(BRIDGE_PATH),
        "consumeWith": "python tools\\poll_scheduler_observation_inbox.py",
    }
    save_json(QUEUE_PATH, queue)
    save_json(STATE_PATH, state)
    save_json(OBS_PATH, [])
    save_json(BRIDGE_PATH, bridge)
    save_json(INBOX_PATH, inbox)


def seed_idle_case():
    save_json(INBOX_PATH, {
        "createdAt": now_local(),
        "kind": "scheduler_observation_inbox",
        "ready": False,
        "status": "idle",
        "messageKey": "",
        "sessionKey": "current",
        "bridgePath": str(BRIDGE_PATH),
        "consumeWith": "python tools\\poll_scheduler_observation_inbox.py",
    })


def main():
    steps = []

    seed_idle_case()
    steps.append({"case": "idle_before_pending", "run": run(["python", "tools\\heartbeat_scheduler_observation.py"]), "result": load_json(HEARTBEAT_RESULT_PATH, {}) or {}})

    seed_pending_case()
    steps.append({"case": "pending_ready", "run": run(["python", "tools\\heartbeat_scheduler_observation.py"]), "result": load_json(HEARTBEAT_RESULT_PATH, {}) or {}})

    steps.append({"case": "idle_after_consumed", "run": run(["python", "tools\\heartbeat_scheduler_observation.py"]), "result": load_json(HEARTBEAT_RESULT_PATH, {}) or {}})

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    inbox = load_json(INBOX_PATH, {}) or {}
    observations = load_json(OBS_PATH, []) or []
    attempts = state.get("toolDeliveryAttempts") or []

    result = {
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "lastAttemptStatus": attempts[-1].get("status", "") if attempts else "",
        "successAttemptCount": len([a for a in attempts if a.get("status") == "success"]),
        "pendingAttemptCount": len([a for a in attempts if a.get("status") == "pending_confirmation"]),
        "observationCount": len(observations),
        "dispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "finalInboxStatus": inbox.get("status", ""),
        "idleBeforePending": steps[0]["result"].get("action") == "idle",
        "pendingWasPolled": steps[1]["result"].get("action") == "polled" and ((steps[1]["result"].get("pollResult") or {}).get("ok") is True),
        "idleAfterConsumed": steps[2]["result"].get("action") == "idle",
    }
    result["closed"] = result["queueLength"] == 0 and not result["hasPendingToolPayload"] and not result["hasPendingConfirmation"] and result["lastError"] == "" and result["lastAttemptStatus"] == "success" and result["successAttemptCount"] == 1 and result["pendingAttemptCount"] == 1 and result["observationCount"] == 1 and result["dispatchRequestStatus"] == "reconciled_success" and result["idleBeforePending"] and result["pendingWasPolled"] and result["idleAfterConsumed"]

    save_json(VALIDATE_RESULT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
