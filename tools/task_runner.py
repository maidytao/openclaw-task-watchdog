import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
TASK_PATH = ROOT / "tasks" / "current-task.json"
RUNNER_STATE = ROOT / "tasks" / "runner-state.json"
REGISTRY_PATH = ROOT / "tasks" / "task-registry.json"
TYPES_PATH = ROOT / "tasks" / "task-types.json"
CFG_PATH = ROOT / "tasks" / "runner-config.json"
TZ = timezone(timedelta(hours=8))


def now_local():
    return datetime.now(TZ)


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_registry_tasks():
    if REGISTRY_PATH.exists():
        data = load_json(REGISTRY_PATH)
        tasks = data.get("tasks", [])
        if tasks:
            return tasks
    return [{"id": None, "taskFile": str(TASK_PATH.relative_to(ROOT)).replace('\\', '/'), "taskType": "generic-resumable"}]


def load_task_types():
    if TYPES_PATH.exists():
        return load_json(TYPES_PATH).get("types", {})
    return {}


def load_runner_cfg():
    if CFG_PATH.exists():
        return load_json(CFG_PATH)
    return {}


def resolve_runner_spec(task, task_types):
    task_type = task.get("taskType") or "generic-resumable"
    type_spec = task_types.get(task_type, {})
    return task_type, type_spec.get("runner", {})


def restart_task(task_data, runner_spec, now_iso, interval_minutes):
    old = task_data.get("currentApproach", "")
    task_data["status"] = runner_spec.get("restartToStatus", "执行中")
    task_data["currentApproach"] = runner_spec.get(
        "defaultRestartApproach",
        "任务重启后新方案：先恢复任务推进机制，再要求进入新的具体执行步骤"
    )
    task_data["blocker"] = runner_spec.get(
        "defaultRestartBlocker",
        "旧方案已失效，已由 task_runner 自动重启为新方案。"
    )
    task_data["nextAction"] = runner_spec.get(
        "defaultRestartNextAction",
        "向用户/主会话明确宣布旧方案失效，并以一个具体可执行步骤重新开始任务。"
    )
    task_data["lastHeartbeatAt"] = now_iso
    task_data["nextUpdateBy"] = (now_local() + timedelta(minutes=interval_minutes)).isoformat()
    task_data["restartCount"] = int(task_data.get("restartCount", 0)) + 1
    return old


def main():
    now_dt = now_local()
    now = now_dt.isoformat()
    cfg = load_runner_cfg()
    interval_minutes = int(cfg.get("intervalMinutes", 5))
    max_restarts_without_progress = int(cfg.get("maxRestartsWithoutProgress", 2))
    task_types = load_task_types()
    registry_tasks = load_registry_tasks()
    state = {"lastRunAt": now, "tasks": []}

    for registered in registry_tasks:
        task_file_rel = registered.get("taskFile") or str(TASK_PATH.relative_to(ROOT)).replace('\\', '/')
        task_file = ROOT / Path(task_file_rel)
        if not task_file.exists():
            state["tasks"].append({
                "taskFile": task_file_rel,
                "action": "missing_task_file"
            })
            continue

        task_data = load_json(task_file)
        status = task_data.get("status")
        task_type, runner_spec = resolve_runner_spec(registered, task_types)
        restart_statuses = runner_spec.get("restartStatus", ["restart_required"])
        task_state = {
            "taskId": task_data.get("taskId") or registered.get("id"),
            "taskFile": task_file_rel,
            "taskType": task_type,
            "observedStatus": status
        }

        last_progress = parse_dt(task_data.get("lastProgressAt"))
        progress_stale = False
        if last_progress and (now_dt - last_progress) > timedelta(minutes=interval_minutes):
            progress_stale = True
        elif not last_progress:
            progress_stale = True

        restart_count = int(task_data.get("restartCount", 0))
        if status in ["已完成", "completed", "done", "failed"]:
            task_state["action"] = "terminal"
        elif status in restart_statuses:
            if progress_stale and restart_count >= max_restarts_without_progress:
                task_data["status"] = "blocked"
                task_data["lastHeartbeatAt"] = now
                task_data["nextUpdateBy"] = (now_dt + timedelta(minutes=interval_minutes)).isoformat()
                task_data["blocker"] = (
                    "Automatic restart circuit breaker engaged: repeated restarts occurred without substantive progress evidence."
                )
                task_data["nextAction"] = (
                    "Stop auto-restarting this task. Require a new execution approach that produces a verifiable output before resuming."
                )
                save_json(task_file, task_data)
                task_state["action"] = "restart_circuit_opened"
                task_state["restartCount"] = restart_count
            else:
                old = restart_task(task_data, runner_spec, now, interval_minutes)
                task_state["action"] = "restarted"
                task_state["previousApproach"] = old
                task_state["restartCount"] = task_data.get("restartCount")
                save_json(task_file, task_data)
        elif status == "blocked":
            task_state["action"] = "observed_blocked"
        else:
            task_state["action"] = "noop"

        state["tasks"].append(task_state)

    save_json(RUNNER_STATE, state)
    print(state["tasks"][0]["action"] if len(state["tasks"]) == 1 else "processed_tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
