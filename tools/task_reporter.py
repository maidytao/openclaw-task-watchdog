import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
CFG_PATH = ROOT / "tasks" / "reporter-config.json"
REGISTRY_PATH = ROOT / "tasks" / "task-registry.json"
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


def build_message(task):
    return {
        "createdAt": now_local(),
        "taskId": task.get("taskId"),
        "status": task.get("status"),
        "message": {
            "status": task.get("status"),
            "deliverable": task.get("deliverable"),
            "blocker": task.get("blocker"),
            "nextAction": task.get("nextAction"),
            "nextUpdateBy": task.get("nextUpdateBy")
        }
    }


def load_registry_tasks(cfg):
    if REGISTRY_PATH.exists():
        data = load_json(REGISTRY_PATH, {}) or {}
        tasks = data.get("tasks", [])
        if tasks:
            return tasks
    return [{"id": None, "taskFile": cfg.get("taskFile", "tasks/current-task.json")}]


def signature_for(task):
    return {
        "status": task.get("status"),
        "blocker": task.get("blocker"),
        "nextAction": task.get("nextAction"),
        "nextUpdateBy": task.get("nextUpdateBy"),
        "restartCount": task.get("restartCount"),
        "executorStepIndex": task.get("executorStepIndex")
    }


def dedupe_queue(queue, mode="latest-per-task"):
    latest_by_key = {}
    for item in queue:
        if mode == "latest-per-task":
            key = item.get("taskId")
        else:
            key = (
                item.get("taskId"),
                item.get("status"),
                ((item.get("message") or {}).get("blocker")),
                ((item.get("message") or {}).get("nextAction"))
            )
        latest_by_key[key] = item
    return list(latest_by_key.values())


def main():
    cfg = load_json(CFG_PATH, {})
    if not cfg.get("enabled", False):
        print("DISABLED")
        return 0

    queue_path = ROOT / cfg.get("queueFile", "tasks/report-queue.json")
    state_path = ROOT / cfg.get("stateFile", "tasks/reporter-state.json")
    archive_path = ROOT / cfg.get("archiveFile", "tasks/report-queue.archive.json")
    max_queue_items = int(cfg.get("maxQueueItems", 50))
    dedupe_mode = cfg.get("dedupeMode", "latest-per-task")

    queue = load_json(queue_path, []) or []
    state = load_json(state_path, {}) or {}
    archive = load_json(archive_path, []) or []
    per_task = state.get("perTask", {})
    queued = []

    queue = dedupe_queue(queue, mode=dedupe_mode)
    if len(queue) > max_queue_items:
        archive.extend(queue[:-max_queue_items])
        queue = queue[-max_queue_items:]

    for registered in load_registry_tasks(cfg):
        task_file_rel = registered.get("taskFile", cfg.get("taskFile", "tasks/current-task.json"))
        task_path = ROOT / task_file_rel
        if not task_path.exists():
            continue
        task = load_json(task_path, {})
        task_id = task.get("taskId") or registered.get("id") or task_file_rel
        signature = signature_for(task)
        last_signature = per_task.get(task_id)

        same_except_time = False
        if last_signature:
            same_except_time = dict(last_signature, nextUpdateBy=None) == dict(signature, nextUpdateBy=None)

        if signature != last_signature and not same_except_time:
            queue.append(build_message(task))
            per_task[task_id] = signature
            queued.append(task_id)

    queue = dedupe_queue(queue, mode=dedupe_mode)
    if len(queue) > max_queue_items:
        archive.extend(queue[:-max_queue_items])
        queue = queue[-max_queue_items:]

    save_json(queue_path, queue)
    save_json(archive_path, archive)
    state["perTask"] = per_task
    state["lastReportAt"] = now_local()
    state["queuedTaskIds"] = queued
    state["queueLength"] = len(queue)
    state["archiveLength"] = len(archive)
    save_json(state_path, state)

    print(json.dumps({"queued": queued, "queueLength": len(queue), "archiveLength": len(archive)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
