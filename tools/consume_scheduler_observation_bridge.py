import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
OUT_PATH = ROOT / "tasks" / "scheduler-observation-consume-result.json"


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


def parse_args():
    parser = argparse.ArgumentParser(description="Consume latest pending scheduler observation bridge")
    parser.add_argument("--source", default="scheduler_bridge_consumer")
    parser.add_argument("--note", default="scheduled delivery observed via bridge consumer")
    parser.add_argument("--reconcile-note", default="reconcile after bridge consumer observed delivery")
    return parser.parse_args()


def main():
    args = parse_args()
    state = load_json(STATE_PATH, {}) or {}
    pending = state.get("pendingConfirmation") or {}
    payload = state.get("pendingToolPayload") or {}
    message_key = pending.get("messageKey") or payload.get("messageKey") or ""

    if not message_key:
        result = {
            "ok": False,
            "reason": "no_pending_confirmation",
        }
        save_json(OUT_PATH, result)
        payload = json.dumps(result, ensure_ascii=False)
        sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
        return 0

    steps = []
    steps.append(run([
        "python",
        "tools\\task_report_sender_confirm_success.py",
        "--source",
        args.source,
        "--note",
        args.note,
    ]))
    steps.append(run([
        "python",
        "tools\\task_report_sender_reconcile.py",
        "--note",
        args.reconcile_note,
    ]))
    steps.append(run([
        "python",
        "tools\\cleanup_stale_report_protocol.py",
    ]))

    final_state = load_json(STATE_PATH, {}) or {}
    result = {
        "ok": True,
        "messageKey": message_key,
        "steps": steps,
        "queueClosed": "pendingConfirmation" not in final_state and "pendingToolPayload" not in final_state,
        "lastError": final_state.get("lastError", ""),
        "lastAttemptStatus": ((final_state.get("toolDeliveryAttempts") or [{}])[-1]).get("status", "") if (final_state.get("toolDeliveryAttempts") or []) else "",
    }
    save_json(OUT_PATH, result)
    payload = json.dumps(result, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
