import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
QUEUE_PATH = ROOT / "tasks" / "report-queue.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
RESULT_PATH = ROOT / "tasks" / "runner-reentry-guard-result.json"


def load_json(path, default=None):
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return default
    return json.loads(raw)


def run(args):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    steps = []
    steps.append(run(["python", "tmp\\report-dispatcher-reset.py"]))
    steps.append(run(["python", "tools\\task_report_sender.py"]))
    steps.append(run(["python", "tools\\task_report_sender_dispatcher.py"]))
    steps.append(run(["python", "tools\\task_report_sender_mark_pending.py"]))
    steps.append(run(["python", "tools\\task_report_sender_confirm_success.py", "--source", "guard_test_observed", "--note", "guard test success observation"]))
    steps.append(run(["python", "tools\\task_report_sender_reconcile.py", "--note", "guard test reconcile to success"]))
    steps.append(run(["python", "tools\\task_report_sender.py"]))
    steps.append(run(["python", "tools\\task_report_sender_dispatcher.py"]))
    steps.append(run(["python", "tools\\task_report_sender_mark_pending.py"]))
    steps.append(run(["python", "tools\\task_report_sender_reconcile.py", "--note", "guard test second reconcile"]))

    state = load_json(STATE_PATH, {}) or {}
    queue = load_json(QUEUE_PATH, []) or []
    request = load_json(REQUEST_PATH, {}) or {}
    observations = load_json(OBS_PATH, []) or []

    result = {
        "steps": steps,
        "queueLength": len(queue),
        "hasPendingToolPayload": "pendingToolPayload" in state,
        "hasPendingConfirmation": "pendingConfirmation" in state,
        "lastError": state.get("lastError", ""),
        "lastAttemptStatus": (state.get("toolDeliveryAttempts") or [{}])[-1].get("status", "") if state.get("toolDeliveryAttempts") else "",
        "successAttemptCount": sum(1 for item in (state.get("toolDeliveryAttempts") or []) if item.get("status") == "success"),
        "dispatchRequestStatus": request.get("status", "") if isinstance(request, dict) else "",
        "observationCount": len(observations),
        "closed": len(queue) == 0 and "pendingToolPayload" not in state and "pendingConfirmation" not in state and state.get("lastError", "") == "",
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
