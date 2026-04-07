import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
TASK_PATH = ROOT / "tasks" / "current-task.json"
REPORT_PATH = ROOT / "tasks" / "full-resilience-acceptance-report.json"
TZ = timezone(timedelta(hours=8))

ROUNDS = [
    {
        "name": "round1_core_recovery",
        "script": "run_resilience_chaos_tests.py",
        "report": "tasks/resilience-chaos-report.json",
    },
    {
        "name": "round2_dirty_state_and_corruption",
        "script": "run_resilience_chaos_tests_round2.py",
        "report": "tasks/resilience-chaos-report-round2.json",
    },
    {
        "name": "round3_incident_surface_and_conflict",
        "script": "run_resilience_chaos_tests_round3.py",
        "report": "tasks/resilience-chaos-report-round3.json",
    },
]


def now_iso():
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


def run_round(script_name: str):
    completed = subprocess.run(
        ["python", "-X", "utf8", str(ROOT / "tools" / script_name)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def update_task(status: str, next_action: str, completion_summary=None):
    data = load_json(TASK_PATH, {}) or {}
    now = now_iso()
    data.update({
        "taskId": "full-resilience-acceptance-2026-04-07",
        "title": "一键总韧性验收",
        "deliverable": "串行执行三轮主动破坏测试并产出总验收报告",
        "status": status,
        "lastHeartbeatAt": now,
        "lastProgressAt": now,
        "blocker": "",
        "nextAction": next_action,
        "nextUpdateBy": "" if status == "已完成" else (datetime.now(TZ) + timedelta(minutes=10)).isoformat(),
        "noProgressHeartbeats": 0,
        "currentApproach": "以统一入口串行执行 round1/round2/round3 并汇总最终评级",
    })
    if completion_summary:
        data["completionEvidence"] = {
            "resultFile": "tasks/full-resilience-acceptance-report.json",
            "resultSummary": completion_summary,
        }
    save_json(TASK_PATH, data)


def main():
    started = now_iso()
    update_task("执行中", "运行一键总韧性验收入口，串行执行三轮测试")

    round_results = []
    overall_ok = True
    total_scenarios = 0
    total_passed = 0

    for idx, round_spec in enumerate(ROUNDS, start=1):
        update_task("执行中", f"执行 {round_spec['name']} ({idx}/{len(ROUNDS)})")
        exec_result = run_round(round_spec["script"])
        report_data = load_json(ROOT / round_spec["report"], {}) or {}
        total_scenarios += int(report_data.get("scenarioCount", 0) or 0)
        total_passed += int(report_data.get("passedCount", 0) or 0)
        round_ok = bool(exec_result.get("returncode") == 0 and report_data.get("overallOk"))
        overall_ok = overall_ok and round_ok
        round_results.append({
            "name": round_spec["name"],
            "script": round_spec["script"],
            "report": round_spec["report"],
            "exec": exec_result,
            "overallOk": report_data.get("overallOk"),
            "passedCount": report_data.get("passedCount"),
            "scenarioCount": report_data.get("scenarioCount"),
            "failedScenarios": report_data.get("failedScenarios", []),
        })

    pass_rate = (total_passed / total_scenarios) if total_scenarios else 0.0
    rating = "A" if pass_rate >= 0.99 else "A-" if pass_rate >= 0.95 else "B+" if pass_rate >= 0.90 else "B"

    report = {
        "status": "ok" if overall_ok else "failed",
        "startedAt": started,
        "finishedAt": now_iso(),
        "overallOk": overall_ok,
        "totalRounds": len(ROUNDS),
        "totalScenarios": total_scenarios,
        "totalPassed": total_passed,
        "passRate": round(pass_rate, 4),
        "rating": rating,
        "rounds": round_results,
        "finalRatingFile": "tasks/resilience-final-rating.json",
    }
    save_json(REPORT_PATH, report)

    update_task(
        "已完成" if overall_ok else "blocked",
        "一键总验收已完成，查看 tasks/full-resilience-acceptance-report.json",
        completion_summary={
            "status": "ok" if overall_ok else "failed",
            "rating": rating,
            "passRate": round(pass_rate, 4),
            "totalPassed": total_passed,
            "totalScenarios": total_scenarios,
            "timestamp": now_iso(),
            "note": "one-click full resilience acceptance finished",
        },
    )

    print(json.dumps({
        "status": report["status"],
        "overallOk": report["overallOk"],
        "totalRounds": report["totalRounds"],
        "totalPassed": report["totalPassed"],
        "totalScenarios": report["totalScenarios"],
        "rating": report["rating"],
    }, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
