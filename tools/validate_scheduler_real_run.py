import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
CFG_PATH = ROOT / "tasks" / "report-delivery-scheduler-config.json"
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
QUEUE_PATH = ROOT / "tasks" / "report-queue.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
LIVE_RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"
SCHED_STATE_PATH = ROOT / "tasks" / "report-delivery-scheduler-state.json"
OUT_PATH = ROOT / "tasks" / "scheduler-real-run-result.json"
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
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def run_schtasks(args):
    return run(["schtasks", *args])


def seed_scheduler_case():
    queue = [
        {
            "taskId": "scheduler-check",
            "status": "执行中",
            "message": {
                "status": "执行中",
                "deliverable": "验证 Scheduled Task 真实 runner 周期",
                "blocker": "",
                "nextAction": "由 Scheduled Task 触发 report-delivery-runner.bat",
                "nextUpdateBy": now_local(),
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


def latest_success(state):
    for attempt in reversed(list(state.get("toolDeliveryAttempts", []) or [])):
        if attempt.get("status") == "success":
            return attempt
    return {}


def main():
    cfg = load_json(CFG_PATH, {}) or {}
    task_name = cfg.get("taskName", "OpenClaw Report Delivery Runner")
    steps = []

    seed_scheduler_case()
    steps.append({"seededAt": now_local(), "taskName": task_name})

    steps.append(run(["python", "tools\\report_delivery_scheduler_status.py"]))
    steps.append(run_schtasks(["/Run", "/TN", task_name]))
    time.sleep(3)
    steps.append(run_schtasks(["/Query", "/TN", task_name, "/V", "/FO", "LIST"]))

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    live_result = load_json(LIVE_RESULT_PATH, {}) or {}
    scheduler_state = load_json(SCHED_STATE_PATH, {}) or {}
    success = latest_success(state)

    result = {
        "checkedAt": now_local(),
        "taskName": task_name,
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "successAttempt": success,
        "liveResultStatus": live_result.get("status", ""),
        "schedulerStateInstalled": scheduler_state.get("installed", False),
        "runnerTriggered": bool(state.get("lastRunAt")),
        "advancedToPendingConfirmation": "pendingConfirmation" in state and state.get("lastError", "") == "pending confirmation after sessions_send timeout",
        "boundary": "scheduled_task_can_trigger_runner_and_drive_to_pending_confirmation_but_cannot_self-observe_chat_delivery",
        "scheduledRunHealthy": bool(state.get("lastRunAt")) and "pendingConfirmation" in state,
    }
    save_json(OUT_PATH, result)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
