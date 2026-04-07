import json
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
REPORT_PATH = ROOT / "tasks" / "resilience-chaos-report-round2.json"
TZ = timezone(timedelta(hours=8))

FILES = {
    "task": ROOT / "tasks" / "current-task.json",
    "queue": ROOT / "tasks" / "report-queue.json",
    "reporter_state": ROOT / "tasks" / "reporter-state.json",
    "sender_state": ROOT / "tasks" / "report-sender-state.json",
    "observations": ROOT / "tasks" / "report-delivery-observations.json",
    "request": ROOT / "tasks" / "report-dispatch-request.json",
    "handoff": ROOT / "tasks" / "report-live-dispatch-handoff.json",
    "plan": ROOT / "tasks" / "report-live-send-plan.json",
    "live_result": ROOT / "tasks" / "report-live-send-result.json",
    "sync_result": ROOT / "tasks" / "report-terminal-sync-result.json",
}


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


def sample_task():
    return {
        "taskId": "resilience-round2-report-task",
        "title": "第二轮韧性测试消息任务",
        "deliverable": "验证报告链路在脏状态下的韧性",
        "status": "执行中",
        "startedAt": now_iso(),
        "lastHeartbeatAt": now_iso(),
        "lastProgressAt": now_iso(),
        "noProgressHeartbeats": 0,
        "currentApproach": "round2",
        "blocker": "",
        "nextAction": "emit report",
        "nextUpdateBy": (datetime.now(TZ) + timedelta(minutes=10)).isoformat(),
        "restartCount": 0,
        "executorStepIndex": 0,
    }


def sample_queue_item(next_update_by=None):
    return {
        "createdAt": now_iso(),
        "taskId": "resilience-round2-report-task",
        "status": "执行中",
        "message": {
            "status": "执行中",
            "deliverable": "验证报告链路在脏状态下的韧性",
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


def payload_key(session_key, msg_key, text):
    return f"{session_key}|{msg_key}|{text}"


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


def scenario_reporter_recovers_invalid_queue_json():
    save_json(FILES["task"], sample_task())
    write_raw(FILES["queue"], "{ bad json")
    result = run_py("task_reporter.py")
    queue = load_json(FILES["queue"], [])
    state = load_json(FILES["reporter_state"], {})
    return {
        "name": "reporter_recovers_invalid_queue_json",
        "inject": "把 report-queue.json 损坏成非法 JSON，再运行 reporter",
        "steps": [result],
        "observed": {
            "queueLength": len(queue or []),
            "queuedTaskIds": state.get("queuedTaskIds"),
            "lastReportAt": state.get("lastReportAt"),
        },
        "pass": result.get("returncode") == 0 and len(queue or []) >= 1,
    }


def scenario_sender_recovers_invalid_state_json():
    item = sample_queue_item()
    save_json(FILES["queue"], [item])
    write_raw(FILES["sender_state"], "not json")
    result = run_py("task_report_sender.py")
    state = load_json(FILES["sender_state"], {})
    return {
        "name": "sender_recovers_invalid_state_json",
        "inject": "把 report-sender-state.json 损坏成非法 JSON，再运行 sender",
        "steps": [result],
        "observed": {
            "lastProcessedCount": state.get("lastProcessedCount"),
            "remainingQueue": len(load_json(FILES['queue'], []) or []),
            "lastError": state.get("lastError"),
        },
        "pass": result.get("returncode") == 0 and state.get("lastProcessedCount") is not None,
    }


def scenario_sender_refreshes_expired_pending_payload():
    expired = sample_queue_item(next_update_by=(datetime.now(TZ) - timedelta(minutes=30)).isoformat())
    save_json(FILES["queue"], [expired])
    save_json(FILES["sender_state"], {})
    result = run_py("task_report_sender.py")
    state = load_json(FILES["sender_state"], {})
    refreshed = state.get("refreshedItems") or []
    return {
        "name": "sender_refreshes_expired_pending_payload",
        "inject": "给 sender 一个已过期 nextUpdateBy 的待发送 payload，验证是否自动刷新",
        "steps": [result],
        "observed": {
            "refreshedItems": refreshed,
            "lastProcessedCount": state.get("lastProcessedCount"),
            "pendingToolPayload": state.get("pendingToolPayload"),
        },
        "pass": result.get("returncode") == 0 and len(refreshed) >= 1,
    }


def scenario_terminal_sync_accepts_pending_only():
    item = sample_queue_item()
    msg_key = message_key(item)
    text = delivery_text(item)
    session_key = "agent:main:feishu:direct:test"
    save_json(FILES["sender_state"], {
        "pendingConfirmation": {
            "sessionKey": session_key,
            "messageKey": msg_key,
        },
        "pendingToolPayload": {
            "sessionKey": session_key,
            "messageKey": msg_key,
            "message": text,
        },
        "toolDeliveryAttempts": [
            {
                "attemptedAt": now_iso(),
                "sessionKey": session_key,
                "messageKey": msg_key,
                "status": "pending_confirmation",
                "note": "synthetic pending",
            }
        ],
        "liveSendPlan": {
            "messageKey": msg_key,
            "status": "created",
        },
        "dispatchRequest": {
            "messageKey": msg_key,
            "status": "created",
        },
        "lastDeliveredPayloadKey": payload_key(session_key, msg_key, text),
    })
    save_json(FILES["request"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["handoff"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["plan"], {"messageKey": msg_key, "status": "created"})
    save_json(FILES["live_result"], {"messageKey": msg_key, "status": "created"})
    result = run_py("sync_report_delivery_terminal_state.py")
    sync = load_json(FILES["sync_result"], {})
    request = load_json(FILES["request"], {})
    plan = load_json(FILES["plan"], {})
    live_result = load_json(FILES["live_result"], {})
    return {
        "name": "terminal_sync_accepts_pending_only",
        "inject": "只提供 pending_confirmation 终态，不提供 success，验证 terminal sync 是否接受该边界",
        "steps": [result],
        "observed": {
            "mode": sync.get("mode"),
            "requestStatus": request.get("status"),
            "planStatus": plan.get("status"),
            "liveResultStatus": live_result.get("status"),
        },
        "pass": sync.get("ok") is True and sync.get("mode") == "pending_confirmation" and request.get("status") == "pending_confirmation",
    }


def scenario_reconcile_survives_invalid_observation_file():
    item = sample_queue_item()
    msg_key = message_key(item)
    text = delivery_text(item)
    session_key = "agent:main:feishu:direct:test"
    save_json(FILES["sender_state"], {
        "pendingConfirmation": {
            "sessionKey": session_key,
            "messageKey": msg_key,
        },
        "pendingToolPayload": {
            "sessionKey": session_key,
            "messageKey": msg_key,
            "message": text,
        },
        "toolDeliveryAttempts": [],
        "lastError": "pending confirmation after sessions_send timeout"
    })
    save_json(FILES["queue"], [item])
    write_raw(FILES["observations"], "[bad observation json")
    result = run_py("task_report_sender_reconcile.py")
    state = load_json(FILES["sender_state"], {})
    return {
        "name": "reconcile_survives_invalid_observation_file",
        "inject": "把 observation 文件损坏，再运行 reconcile，验证不会崩溃且保持 pending",
        "steps": [result],
        "observed": {
            "hasPendingConfirmation": "pendingConfirmation" in state,
            "hasPendingToolPayload": "pendingToolPayload" in state,
            "lastError": state.get("lastError"),
        },
        "pass": result.get("returncode") == 0 and ("pendingConfirmation" in state),
    }


def main():
    backup = backup_all()
    scenarios = []
    started = now_iso()
    try:
        scenarios.append(scenario_reporter_recovers_invalid_queue_json())
        scenarios.append(scenario_sender_recovers_invalid_state_json())
        scenarios.append(scenario_sender_refreshes_expired_pending_payload())
        scenarios.append(scenario_terminal_sync_accepts_pending_only())
        scenarios.append(scenario_reconcile_survives_invalid_observation_file())
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
    print(json.dumps({
        "status": report["status"],
        "overallOk": report["overallOk"],
        "passedCount": report["passedCount"],
        "scenarioCount": report["scenarioCount"],
    }, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
