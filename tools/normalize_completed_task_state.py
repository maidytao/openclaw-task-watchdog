import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
REGISTRY_PATH = ROOT / "tasks" / "task-registry.json"
DEFAULT_TASK_PATH = ROOT / "tasks" / "current-task.json"
OUT_PATH = ROOT / "tasks" / "completed-task-normalization-result.json"
TZ = timezone(timedelta(hours=8))
TERMINAL_STATUSES = {"已完成", "completed", "done", "failed"}


def now_local():
    return datetime.now(TZ).isoformat()


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


def iter_task_files():
    registry = load_json(REGISTRY_PATH, {}) or {}
    tasks = registry.get("tasks", []) or []
    if not tasks:
        return [DEFAULT_TASK_PATH]
    files = []
    for item in tasks:
        rel = item.get("taskFile", "tasks/current-task.json")
        files.append(ROOT / rel)
    return files


def normalize_task(task):
    status = task.get("status")
    result_summary = ((task.get("completionEvidence") or {}).get("resultSummary") or {})
    is_terminal = status in TERMINAL_STATUSES or result_summary.get("status") == "ok"
    if not is_terminal:
        return False

    changed = False
    if status != "已完成" and result_summary.get("status") == "ok":
        task["status"] = "已完成"
        changed = True

    if task.get("blocker"):
        task["blocker"] = ""
        changed = True

    desired_next_action = "No further action required. Task has verifiable completion evidence." if result_summary.get("status") == "ok" else "No further action required. Task is in terminal state."
    if task.get("nextAction") != desired_next_action:
        task["nextAction"] = desired_next_action
        changed = True

    if int(task.get("noProgressHeartbeats", 0)) != 0:
        task["noProgressHeartbeats"] = 0
        changed = True

    if task.get("nextUpdateBy"):
        task["nextUpdateBy"] = ""
        changed = True

    if not task.get("normalizedCompletedAt"):
        task["normalizedCompletedAt"] = now_local()
        changed = True

    return changed


def main():
    updated = []
    skipped = []
    for path in iter_task_files():
        if not path.exists():
            skipped.append({"taskFile": str(path), "reason": "missing"})
            continue
        task = load_json(path, {}) or {}
        changed = normalize_task(task)
        if changed:
            save_json(path, task)
            updated.append({"taskFile": str(path), "status": task.get("status")})
        else:
            skipped.append({"taskFile": str(path), "reason": "unchanged", "status": task.get("status")})

    result = {
        "checkedAt": now_local(),
        "updated": updated,
        "skipped": skipped,
    }
    save_json(OUT_PATH, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
