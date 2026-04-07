import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
TASK_PATH = ROOT / "tasks" / "current-task.json"
CFG_PATH = ROOT / "tasks" / "executor-config.json"
ACTIONS_PATH = ROOT / "tasks" / "executor-actions.json"
STATE_PATH = ROOT / "tasks" / "executor-state.json"
REGISTRY_PATH = ROOT / "tasks" / "task-registry.json"
TYPES_PATH = ROOT / "tasks" / "task-types.json"
TZ = timezone(timedelta(hours=8))


def now_local():
    return datetime.now(TZ)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_handler(task_id, handlers):
    for name, handler in handlers.items():
        marker = handler.get("match", "")
        if marker and marker in task_id:
            return name, handler
    return None, None


def run_powershell(command: str):
    completed = subprocess.run([
        "powershell", "-NoProfile", "-Command", command
    ], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:]
    }


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


def get_legacy_handler(task, cfg):
    handlers = cfg.get("handlers", {})
    task_id = task.get("taskId", "")
    name, handler = resolve_handler(task_id, handlers)
    if not handler:
        return None
    return {
        "name": name,
        "plan": handler.get("plan", []),
        "actionsRef": name
    }


def get_task_spec(registered, task, cfg, task_types):
    task_type = registered.get("taskType") or task.get("taskType") or "generic-resumable"
    type_spec = task_types.get(task_type, {})
    executor_spec = type_spec.get("executor")
    if executor_spec:
        return task_type, executor_spec
    legacy = get_legacy_handler(task, cfg)
    if legacy:
        return legacy["name"], legacy
    return task_type, None


def main():
    if not CFG_PATH.exists():
        print("MISSING_INPUT")
        return 0

    cfg = load_json(CFG_PATH)
    actions_cfg = load_json(ACTIONS_PATH) if ACTIONS_PATH.exists() else {}
    task_types = load_task_types()
    registry_tasks = load_registry_tasks()
    now = now_local().isoformat()
    state = {"lastRunAt": now, "tasks": []}

    for registered in registry_tasks:
        task_file_rel = registered.get("taskFile") or str(TASK_PATH.relative_to(ROOT)).replace('\\', '/')
        task_file = ROOT / Path(task_file_rel)
        task_state = {
            "taskFile": task_file_rel,
            "action": "noop"
        }

        if not task_file.exists():
            task_state["action"] = "missing_task_file"
            state["tasks"].append(task_state)
            continue

        task = load_json(task_file)
        task_id = task.get("taskId", "")
        handler_name, handler = get_task_spec(registered, task, cfg, task_types)
        task_state.update({
            "taskId": task_id,
            "handler": handler_name
        })

        if not handler:
            task_state["action"] = "no_handler"
            state["tasks"].append(task_state)
            continue

        plan = handler.get("plan", [])
        step_index = int(task.get("executorStepIndex", 0))
        if step_index < len(plan):
            task["status"] = "执行中"
            task["nextAction"] = plan[step_index]
            task["executorStepIndex"] = step_index + 1
            task["lastHeartbeatAt"] = now
            task["nextUpdateBy"] = (now_local() + timedelta(minutes=5)).isoformat()
            task_state["action"] = "advanced_step"
            task_state["step"] = plan[step_index]
            save_json(task_file, task)
            state["tasks"].append(task_state)
            continue

        action_ref = handler.get("actionsRef") or handler_name
        action_plan = actions_cfg.get(action_ref, {})
        steps = action_plan.get("steps", [])
        action_index = int(task.get("executorActionIndex", 0))
        if action_index < len(steps):
            step = steps[action_index]
            result = None
            if step.get("type") == "command":
                result = run_powershell(step.get("command", ""))
            task["executorActionIndex"] = action_index + 1
            task["lastHeartbeatAt"] = now
            task["nextUpdateBy"] = (now_local() + timedelta(minutes=5)).isoformat()
            task["lastExecutorActionName"] = step.get("name")
            task_state["action"] = "executed_action"
            task_state["step"] = step.get("name")
            task_state["result"] = result
            save_json(task_file, task)
            state["tasks"].append(task_state)
            continue

        task_state["action"] = "plan_exhausted"
        state["tasks"].append(task_state)

    save_json(STATE_PATH, state)
    print(state["tasks"][0]["action"] if len(state["tasks"]) == 1 else "processed_tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
