import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
QUEUE_PATH = ROOT / "tasks" / "report-queue.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
HANDOFF_PATH = ROOT / "tasks" / "report-live-dispatch-handoff.json"
PLAN_PATH = ROOT / "tasks" / "report-live-send-plan.json"
LIVE_RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"
RESULT_PATH = ROOT / "tasks" / "runner-stability-result.json"


def load_json(path, default=None):
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return default
    return json.loads(raw)


def run(args, shell=False):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=shell)
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    steps = []
    steps.append(run(["python", "tmp\\report-dispatcher-reset.py"]))
    steps.append(run(["python", "tools\\task_report_sender.py"]))
    steps.append(run(["python", "tools\\task_report_sender_dispatcher.py"]))
    steps.append(run(["python", "tools\\task_report_sender_mark_pending.py"]))
    steps.append(run(["python", "tools\\task_report_sender_confirm_success.py", "--source", "runner_stability_observed", "--note", "runner stability observed success"]))
    steps.append(run("tasks\\report-delivery-runner.bat", shell=True))
    steps.append(run("tasks\\report-delivery-runner.bat", shell=True))
    steps.append(run("tasks\\report-delivery-runner.bat", shell=True))

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    observations = load_json(OBS_PATH, []) or []
    request_exists = REQUEST_PATH.exists()
    handoff_exists = HANDOFF_PATH.exists()
    plan_exists = PLAN_PATH.exists()
    live_result = load_json(LIVE_RESULT_PATH, {}) or {}
    attempts = state.get("toolDeliveryAttempts") or []

    result = {
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "attemptStatuses": [item.get("status", "") for item in attempts],
        "successAttemptCount": sum(1 for item in attempts if item.get("status") == "success"),
        "pendingAttemptCount": sum(1 for item in attempts if item.get("status") == "pending_confirmation"),
        "requestExists": request_exists,
        "handoffExists": handoff_exists,
        "planExists": plan_exists,
        "liveResultStatus": live_result.get("status", ""),
        "observationCount": len(observations),
        "stable": len(queue) == 0 and "pendingToolPayload" not in state and "pendingConfirmation" not in state and state.get("lastError", "") == "" and not request_exists and not handoff_exists and not plan_exists and live_result.get("status", "") == "reconciled_success",
    }
    write_json(RESULT_PATH, result)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
