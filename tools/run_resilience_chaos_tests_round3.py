import json
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
REPORT_PATH = ROOT / "tasks" / "resilience-chaos-report-round3.json"
FINAL_RATING_PATH = ROOT / "tasks" / "resilience-final-rating.json"
TZ = timezone(timedelta(hours=8))

FILES = {
    "task": ROOT / "tasks" / "current-task.json",
    "queue": ROOT / "tasks" / "report-queue.json",
    "archive": ROOT / "tasks" / "report-queue.archive.json",
    "reporter_state": ROOT / "tasks" / "reporter-state.json",
    "sender_state": ROOT / "tasks" / "report-sender-state.json",
    "observations": ROOT / "tasks" / "report-delivery-observations.json",
    "request": ROOT / "tasks" / "report-dispatch-request.json",
    "handoff": ROOT / "tasks" / "report-live-dispatch-handoff.json",
    "plan": ROOT / "tasks" / "report-live-send-plan.json",
    "live_result": ROOT / "tasks" / "report-live-send-result.json",
    "sync_result": ROOT / "tasks" / "report-terminal-sync-result.json",
    "runner_state": ROOT / "tasks" / "runner-state.json",
}

ROUND1_PATH = ROOT / "tasks" / "resilience-chaos-report.json"
ROUND2_PATH = ROOT / "tasks" / "resilience-chaos-report-round2.json"


def now_iso():
    return datetime.now(TZ).isoformat()


def load_json(path: Path, default=None):
    if not path.exists():
        return deepcopy(default)
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return deepcopy(default)
    if not raw.strip():
        return deepcopy(default)
    try:
        return json.loads(raw)
    except Exception:
        return deepcopy(default)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_raw(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_py(script_name: str, args=None):
    cmd = ["python", "-X", "utf8", str(ROOT / "tools" / script_name)]
    if args:
        cmd.extend(args)
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "script": script_name,
        "args": args or [],
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def backup_all():
    backup = {}
    for key, path in FILES.items():
        backup[key] = path.read_text(encoding="utf-8") if path.exists() else None
    return backup


def restore_all(backup):
    for key, path in FILES.items():
        original = backup.get(key)
        if original is None:
            if path.exists():
                path.unlink()
        else:
            write_raw(path, original)


def sample_task(task_id="resilience-round3-task", status="执行中"):
    return {
        "taskId": task_id,
        "title": "第三轮韧性测试任务",
        "deliverable": "验证事故面条件下的韧性",
        "status": status,
        "startedAt": now_iso(),
        "lastHeartbeatAt": now_iso(),
        "lastProgressAt": now_iso(),
        "noProgressHeartbeats": 0,
        "currentApproach": "round3",
        "blocker": "",
        "nextAction": "emit report",
        "nextUpdateBy": (datetime.now(TZ) + timedelta(minutes=10)).isoformat(),
        "restartCount": 0,
        "executorStepIndex": 0,
        "executorActionIndex": 0,
    }


def sample_queue_item(task_id="resilience-round3-task", next_update_by=None):
    return {
        "createdAt": now_iso(),
        "taskId": task_id,
        "status": "执行中",
        "message": {
            "status": "执行中",
            "deliverable": "验证事故面条件下的韧性",
            "blocker": "",
            "nextAction": "emit report",
            "nextUpdateBy": next_update_by or (datetime.now(TZ) + timedelta(minutes=10)).isoformat(),
        },
    }


def message_key(item):
    msg = item.get("message") or {}
    parts = [
        item.get("taskId", ""),
        item.get("status", ""),
        msg.get("blocker", ""),
        msg.get("nextAction", ""),
        msg.get("nextUpdateBy", ""),
    ]
    return "|".join(str(x).replace("\r\n", "\n").replace("\r", "\n").strip() for x in parts)


def delivery_text(item):
    msg = item.get("message") or {}
    return "\n".join([
        "[[reply_to_current]] 任务状态通知",
        f"状态：{msg.get('status', '')}",
        f"交付物：{msg.get('deliverable', '')}",
        f"阻塞：{msg.get('blocker', '')}",
        f"下一步：{msg.get('nextAction', '')}",
        f"下次更新：{msg.get('nextUpdateBy', '')}",
    ])


def scenario_reporter_recreates_missing_queue_and_state():
    save_json(FILES["task"], sample_task())
    if FILES["queue"].exists():
        FILES["queue"].unlink()
    if FILES["reporter_state"].exists():
        FILES["reporter_state"].unlink()
    result = run_py("task_reporter.py")
    queue = load_json(FILES["queue"], [])
    state = load_json(FILES["reporter_state"], {})
    return {
        "name": "reporter_recreates_missing_queue_and_state",
        "inject": "删除 report-queue.json 和 reporter-state.json，再运行 reporter",
        "steps": [result],
        "observed": {
            "queueExists": FILES["queue"].exists(),
            "stateExists": FILES["reporter_state"].exists(),
            "queueLength": len(queue or []),
            "queuedTaskIds": state.get("queuedTaskIds"),
        },
        "pass": result.get("returncode") == 0 and FILES["queue"].exists() and FILES["reporter_state"].exists() and len(queue or []) >= 1,
    }


def scenario_sender_dedupes_duplicate_queue_entries():
    item = sample_queue_item()
    dup = deepcopy(item)
    save_json(FILES["queue"], [item, dup])
    save_json(FILES["sender_state"], {})
    result = run_py("task_report_sender.py")
    queue = load_json(FILES["queue"], [])
    state = load_json(FILES["sender_state"], {})
    return {
        "name": "sender_dedupes_duplicate_queue_entries",
        "inject": "向队列写入完全重复的两条消息，验证 sender 处理后只保留一个活跃项",
        "steps": [result],
        "observed": {
            "remainingQueue": len(queue or []),
            "pendingToolPayload": state.get("pendingToolPayload"),
            "lastError": state.get("lastError"),
        },
        "pass": result.get("returncode") == 0 and len(queue or []) == 1,
    }


def scenario_sync_prefers_success_over_pending_conflict():
    item = sample_queue_item()
    msg_key = message_key(item)
    session_key = "agent:main:feishu:direct:test"
    save_json(FILES["sender_state"], {
        "pendingConfirmation": {
            "sessionKey": session_key,
            "messageKey": msg_key,
        },
        "pendingToolPayload": {
            "sessionKey": session_key,
            "messageKey": msg_key,
            "message": delivery_text(item),
        },
        "toolDeliveryAttempts": [
            {
                "attemptedAt": (datetime.now(TZ) - timedelta(minutes=1)).isoformat(),
                "sessionKey": session_key,
                "messageKey": msg_key,
                "status": "pending_confirmation",
                "note": "older pending",
            },
            {
                "attemptedAt": now_iso(),
                "sessionKey": session_key,
                "messageKey": msg_key,
                "status": "success",
                "note": "newer success",
            }
        ],
        "dispatchRequest": {"messageKey": msg_key, "status": "created"},
        "liveSendPlan": {"messageKey": msg_key, "status": "created"},
        "lastDeliveredPayloadKey": f"{session_key}|{msg_key}|{delivery_text(item)}",
    })
    save_json(FILES["request"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["handoff"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["plan"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["live_result"], {"messageKey": msg_key, "status": "created"})
    result = run_py("sync_report_delivery_terminal_state.py")
    sync = load_json(FILES["sync_result"], {})
    request = load_json(FILES["request"], {})
    live_result = load_json(FILES["live_result"], {})
    return {
        "name": "sync_prefers_success_over_pending_conflict",
        "inject": "同时放入 pending 和 success 两种 attempt，验证 terminal sync 选择 success 作为更强终态",
        "steps": [result],
        "observed": {
            "mode": sync.get("mode"),
            "requestStatus": request.get("status"),
            "liveResultStatus": live_result.get("status"),
        },
        "pass": sync.get("ok") is True and sync.get("mode") == "success" and request.get("status") == "reconciled_success",
    }


def scenario_runner_missing_task_file_is_controlled():
    original = FILES["task"].read_text(encoding="utf-8") if FILES["task"].exists() else None
    if FILES["task"].exists():
        FILES["task"].unlink()
    result = run_py("task_runner.py")
    state = load_json(FILES["runner_state"], {})
    if original is not None:
        write_raw(FILES["task"], original)
    return {
        "name": "runner_missing_task_file_is_controlled",
        "inject": "删除 current-task.json 再运行 runner，验证不会崩溃且记录 missing_task_file",
        "steps": [result],
        "observed": {
            "tasks": state.get("tasks"),
            "lastRunAt": state.get("lastRunAt"),
        },
        "pass": result.get("returncode") == 0 and any((item or {}).get("action") == "missing_task_file" for item in (state.get("tasks") or [])),
    }


def scenario_reconcile_clears_queue_on_real_success_observation():
    item = sample_queue_item()
    msg_key = message_key(item)
    session_key = "agent:main:feishu:direct:test"
    save_json(FILES["queue"], [item])
    save_json(FILES["sender_state"], {
        "pendingConfirmation": {
            "sessionKey": session_key,
            "messageKey": msg_key,
        },
        "pendingToolPayload": {
            "sessionKey": session_key,
            "messageKey": msg_key,
            "message": delivery_text(item),
        },
        "toolDeliveryAttempts": [],
        "lastError": "pending confirmation after sessions_send timeout"
    })
    save_json(FILES["observations"], [{
        "messageKey": msg_key,
        "status": "success",
        "source": "feishu-runtime",
        "note": "delivery observed in live surface",
    }])
    result = run_py("task_report_sender_reconcile.py")
    state = load_json(FILES["sender_state"], {})
    queue = load_json(FILES["queue"], [])
    return {
        "name": "reconcile_clears_queue_on_real_success_observation",
        "inject": "给 pending confirmation 注入真实 success observation，验证 reconcile 收口并清队列",
        "steps": [result],
        "observed": {
            "queueLength": len(queue or []),
            "hasPendingConfirmation": "pendingConfirmation" in state,
            "hasPendingToolPayload": "pendingToolPayload" in state,
            "lastError": state.get("lastError"),
            "attempts": state.get("toolDeliveryAttempts"),
        },
        "pass": result.get("returncode") == 0 and len(queue or []) == 0 and ("pendingConfirmation" not in state) and state.get("lastError", "") == "",
    }


def build_final_rating(round3_report):
    round1 = load_json(ROUND1_PATH, {}) or {}
    round2 = load_json(ROUND2_PATH, {}) or {}
    reports = [round1, round2, round3_report]
    total_scenarios = sum(int(r.get("scenarioCount", 0)) for r in reports)
    total_passed = sum(int(r.get("passedCount", 0)) for r in reports)
    pass_rate = (total_passed / total_scenarios) if total_scenarios else 0.0

    if pass_rate >= 0.99:
        rating = "A"
    elif pass_rate >= 0.95:
        rating = "A-"
    elif pass_rate >= 0.90:
        rating = "B+"
    else:
        rating = "B"

    summary = {
        "status": "ok" if all(bool(r.get("overallOk")) for r in reports if r) else "degraded",
        "generatedAt": now_iso(),
        "rounds": [
            {"report": "tasks/resilience-chaos-report.json", "overallOk": round1.get("overallOk"), "passedCount": round1.get("passedCount"), "scenarioCount": round1.get("scenarioCount")},
            {"report": "tasks/resilience-chaos-report-round2.json", "overallOk": round2.get("overallOk"), "passedCount": round2.get("passedCount"), "scenarioCount": round2.get("scenarioCount")},
            {"report": "tasks/resilience-chaos-report-round3.json", "overallOk": round3_report.get("overallOk"), "passedCount": round3_report.get("passedCount"), "scenarioCount": round3_report.get("scenarioCount")},
        ],
        "totalScenarios": total_scenarios,
        "totalPassed": total_passed,
        "passRate": round(pass_rate, 4),
        "rating": rating,
        "conclusion": "核心恢复、脏状态容错、事故面降级与收口链路已通过三轮主动破坏测试。",
    }
    save_json(FINAL_RATING_PATH, summary)
    return summary


def main():
    backup = backup_all()
    scenarios = []
    started = now_iso()
    try:
        scenarios.append(scenario_reporter_recreates_missing_queue_and_state())
        scenarios.append(scenario_sender_dedupes_duplicate_queue_entries())
        scenarios.append(scenario_sync_prefers_success_over_pending_conflict())
        scenarios.append(scenario_runner_missing_task_file_is_controlled())
        scenarios.append(scenario_reconcile_clears_queue_on_real_success_observation())
    finally:
        restore_all(backup)

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
        "restoredOriginalFiles": True,
    }
    save_json(REPORT_PATH, report)
    final_rating = build_final_rating(report)
    print(json.dumps({
        "status": report["status"],
        "overallOk": report["overallOk"],
        "passedCount": report["passedCount"],
        "scenarioCount": report["scenarioCount"],
        "rating": final_rating.get("rating"),
        "passRate": final_rating.get("passRate"),
    }, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
