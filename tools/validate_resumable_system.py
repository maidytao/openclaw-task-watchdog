import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
OUT_PATH = ROOT / "tasks" / "resumable-system-test-report.json"


def run(args, shell=False):
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=shell)
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return default
    return json.loads(raw)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    steps = []
    steps.append(run(["python", "tools\\normalize_completed_task_state.py"]))
    steps.append(run(["python", "tools\\validate_runner_heartbeat_smoke.py"]))
    steps.append(run(["python", "tools\\validate_runner_reentry_guard.py"]))
    steps.append(run(["python", "tools\\validate_runner_stability.py"]))
    steps.append(run(["python", "tools\\validate_scheduler_real_run.py"]))
    steps.append(run(["python", "tools\\validate_terminal_state_sync.py"]))

    heartbeat = load_json(ROOT / "tasks" / "runner-heartbeat-smoke-result.json", {}) or {}
    reentry = load_json(ROOT / "tasks" / "runner-reentry-guard-result.json", {}) or {}
    stability = load_json(ROOT / "tasks" / "runner-stability-result.json", {}) or {}
    scheduler = load_json(ROOT / "tasks" / "scheduler-real-run-result.json", {}) or {}
    terminal_sync = load_json(ROOT / "tasks" / "report-terminal-sync-result.json", {}) or {}
    normalization = load_json(ROOT / "tasks" / "completed-task-normalization-result.json", {}) or {}
    current_task = load_json(ROOT / "tasks" / "current-task.json", {}) or {}

    checks = {
        "normalization_ok": bool(normalization.get("updated") or normalization.get("skipped")),
        "heartbeat_closure_ok": bool(heartbeat.get("closed")),
        "reentry_guard_ok": bool(reentry.get("closed")),
        "stability_ok": bool(stability.get("stable")),
        "scheduler_trigger_ok": bool(scheduler.get("schedulerStateInstalled")) and bool(scheduler.get("runnerTriggered")),
        "terminal_sync_ok": bool(terminal_sync.get("synced")) or bool((load_json(ROOT / "tasks" / "report-terminal-sync-result.json", {}) or {}).get("ok")),
        "completed_task_clean_ok": current_task.get("status") == "已完成" and int(current_task.get("noProgressHeartbeats", 0)) == 0 and not current_task.get("blocker"),
    }

    overall_ok = all(checks.values())

    report = {
        "overallOk": overall_ok,
        "checks": checks,
        "artifacts": {
            "normalization": normalization,
            "heartbeat": heartbeat,
            "reentry": reentry,
            "stability": stability,
            "scheduler": scheduler,
            "terminalSync": terminal_sync,
            "currentTask": current_task,
        },
        "steps": steps,
        "summary": {
            "status": "ok" if overall_ok else "needs_followup",
            "note": "Scheduler trigger is judged by installation + runner execution, not by whether the test catches a transient pending state.",
        },
    }

    save_json(OUT_PATH, report)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
