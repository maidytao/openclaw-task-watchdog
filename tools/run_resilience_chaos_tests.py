import json
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
TASK_PATH = ROOT / "tasks" / "current-task.json"
REPORT_PATH = ROOT / "tasks" / "resilience-chaos-report.json"
TZ = timezone(timedelta(hours=8))


def now_iso():
    return datetime.now(TZ).isoformat()


def load_json(path: Path, default=None):
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_py(script_name: str):
    completed = subprocess.run(
        ["python", "-X", "utf8", str(ROOT / "tools" / script_name)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "script": script_name,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def make_base_task(task_id: str, status: str = "执行中"):
    return {
        "taskId": task_id,
        "title": "韧性测试临时任务",
        "deliverable": "验证主动破坏后的自动恢复行为",
        "status": status,
        "startedAt": now_iso(),
        "lastHeartbeatAt": (datetime.now(TZ) - timedelta(minutes=30)).isoformat(),
        "lastProgressAt": (datetime.now(TZ) - timedelta(minutes=30)).isoformat(),
        "noProgressHeartbeats": 0,
        "currentApproach": "执行韧性测试",
        "blocker": "",
        "nextAction": "等待测试脚本推进",
        "nextUpdateBy": (datetime.now(TZ) - timedelta(minutes=20)).isoformat(),
        "restartCount": 0,
        "executorStepIndex": 0,
        "executorActionIndex": 0,
        "lastExecutorActionName": "",
    }


def scenario_overdue_to_restart_required():
    task = make_base_task("complex-resume-closure-validation-chaos-timeout")
    save_json(TASK_PATH, task)
    first = run_py("task_heartbeat.py")
    after_first = load_json(TASK_PATH, {})
    second = run_py("task_heartbeat.py")
    after_second = load_json(TASK_PATH, {})
    return {
        "name": "overdue_to_restart_required",
        "inject": "构造超时且无实质进展的执行中任务，连续触发两次 heartbeat",
        "steps": [first, second],
        "observed": {
            "afterFirstStatus": after_first.get("status"),
            "afterFirstNoProgress": after_first.get("noProgressHeartbeats"),
            "afterSecondStatus": after_second.get("status"),
            "afterSecondNoProgress": after_second.get("noProgressHeartbeats"),
            "afterSecondBlocker": after_second.get("blocker"),
        },
        "pass": after_first.get("status") == "blocked" and after_second.get("status") == "restart_required",
    }


def scenario_runner_recovers_restart_required():
    task = make_base_task("complex-resume-closure-validation-chaos-runner", status="restart_required")
    task["restartCount"] = 0
    save_json(TASK_PATH, task)
    run_result = run_py("task_runner.py")
    after = load_json(TASK_PATH, {})
    return {
        "name": "runner_recovers_restart_required",
        "inject": "直接把任务置为 restart_required，验证 runner 是否重启为执行中并切换方案",
        "steps": [run_result],
        "observed": {
            "status": after.get("status"),
            "restartCount": after.get("restartCount"),
            "currentApproach": after.get("currentApproach"),
            "blocker": after.get("blocker"),
            "nextAction": after.get("nextAction"),
        },
        "pass": after.get("status") == "执行中" and int(after.get("restartCount", 0)) >= 1,
    }


def scenario_executor_advance_after_restart():
    task = make_base_task("complex-resume-closure-validation-chaos-executor", status="restart_required")
    save_json(TASK_PATH, task)
    runner = run_py("task_runner.py")
    executor = run_py("task_executor.py")
    after = load_json(TASK_PATH, {})
    return {
        "name": "executor_advance_after_restart",
        "inject": "先让 runner 重启任务，再让 executor 推进一步骤",
        "steps": [runner, executor],
        "observed": {
            "status": after.get("status"),
            "executorStepIndex": after.get("executorStepIndex"),
            "nextAction": after.get("nextAction"),
            "lastHeartbeatAt": after.get("lastHeartbeatAt"),
        },
        "pass": after.get("status") == "执行中" and int(after.get("executorStepIndex", 0)) >= 1,
    }


def scenario_completion_evidence_closes_task():
    task = make_base_task("complex-resume-closure-validation-chaos-evidence", status="执行中")
    task["completionEvidence"] = {
        "resultFile": "tasks/fake-chaos-result.json",
        "resultSummary": {
            "status": "ok",
            "task": "fake-chaos",
            "timestamp": now_iso(),
            "proof": "synthetic"
        }
    }
    save_json(TASK_PATH, task)
    heartbeat = run_py("task_heartbeat.py")
    after = load_json(TASK_PATH, {})
    return {
        "name": "completion_evidence_closes_task",
        "inject": "注入可验证完成证据，验证 heartbeat 是否直接收口为已完成",
        "steps": [heartbeat],
        "observed": {
            "status": after.get("status"),
            "noProgressHeartbeats": after.get("noProgressHeartbeats"),
            "blocker": after.get("blocker"),
            "nextAction": after.get("nextAction"),
        },
        "pass": after.get("status") == "已完成" and int(after.get("noProgressHeartbeats", 0)) == 0,
    }


def scenario_runner_circuit_breaker():
    task = make_base_task("complex-resume-closure-validation-chaos-circuit", status="restart_required")
    task["restartCount"] = 2
    task["lastProgressAt"] = (datetime.now(TZ) - timedelta(minutes=30)).isoformat()
    save_json(TASK_PATH, task)
    runner = run_py("task_runner.py")
    after = load_json(TASK_PATH, {})
    return {
        "name": "runner_circuit_breaker",
        "inject": "构造重复重启且无进展的任务，验证 runner 是否打开断路器转 blocked",
        "steps": [runner],
        "observed": {
            "status": after.get("status"),
            "restartCount": after.get("restartCount"),
            "blocker": after.get("blocker"),
            "nextAction": after.get("nextAction"),
        },
        "pass": after.get("status") == "blocked" and "circuit breaker" in (after.get("blocker") or ""),
    }


def main():
    original_task = load_json(TASK_PATH, {})
    backup_path = ROOT / "tasks" / "current-task.chaos-backup.json"
    save_json(backup_path, original_task)
    scenarios = []
    started = now_iso()
    try:
        scenarios.append(scenario_overdue_to_restart_required())
        scenarios.append(scenario_runner_recovers_restart_required())
        scenarios.append(scenario_executor_advance_after_restart())
        scenarios.append(scenario_completion_evidence_closes_task())
        scenarios.append(scenario_runner_circuit_breaker())
    finally:
        save_json(TASK_PATH, original_task)

    overall_ok = all(item.get("pass") for item in scenarios)
    report = {
        "status": "ok" if overall_ok else "failed",
        "startedAt": started,
        "finishedAt": now_iso(),
        "overallOk": overall_ok,
        "scenarioCount": len(scenarios),
        "passedCount": sum(1 for item in scenarios if item.get("pass")),
        "failedScenarios": [item["name"] for item in scenarios if not item.get("pass")],
        "scenarios": scenarios,
        "restoredOriginalTask": True,
        "backupFile": str(backup_path.relative_to(ROOT)).replace('\\', '/'),
    }
    save_json(REPORT_PATH, report)
    print(json.dumps({
        "status": report["status"],
        "overallOk": report["overallOk"],
        "passedCount": report["passedCount"],
        "scenarioCount": report["scenarioCount"],
    }, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
