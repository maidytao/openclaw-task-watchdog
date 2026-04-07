import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
RESULT_PATH = ROOT / "tasks" / "terminal-state-sync-e2e-result.json"
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
REQUEST_PATH = ROOT / "tasks" / "report-dispatch-request.json"
HANDOFF_PATH = ROOT / "tasks" / "report-live-dispatch-handoff.json"
PLAN_PATH = ROOT / "tasks" / "report-live-send-plan.json"
LIVE_RESULT_PATH = ROOT / "tasks" / "report-live-send-result.json"


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
    steps.append(run(["python", "tools\\sync_report_delivery_terminal_state.py"]))

    state = load_json(STATE_PATH, {}) or {}
    request = load_json(REQUEST_PATH, {}) or {}
    handoff = load_json(HANDOFF_PATH, {}) or {}
    plan = load_json(PLAN_PATH, {}) or {}
    live_result = load_json(LIVE_RESULT_PATH, {}) or {}

    acceptable_statuses = {"reconciled_success", "pending_confirmation", "", None}
    result = {
        "steps": steps,
        "stateDispatchRequestStatus": (state.get("dispatchRequest") or {}).get("status", ""),
        "stateLiveSendPlanStatus": (state.get("liveSendPlan") or {}).get("status", ""),
        "requestStatus": request.get("status", "") if isinstance(request, dict) else "",
        "handoffStatus": handoff.get("status", "") if isinstance(handoff, dict) else "",
        "planStatus": plan.get("status", "") if isinstance(plan, dict) else "",
        "liveResultStatus": live_result.get("status", "") if isinstance(live_result, dict) else "",
        "synced": all(status in acceptable_statuses for status in [
            (state.get("dispatchRequest") or {}).get("status", ""),
            (state.get("liveSendPlan") or {}).get("status", ""),
            request.get("status", "") if isinstance(request, dict) else "",
            handoff.get("status", "") if isinstance(handoff, dict) else "",
            plan.get("status", "") if isinstance(plan, dict) else "",
            live_result.get("status", "") if isinstance(live_result, dict) else "",
        ]),
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
