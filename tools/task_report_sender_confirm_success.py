import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
STATE_PATH = ROOT / "tasks" / "report-sender-state.json"
OBS_PATH = ROOT / "tasks" / "report-delivery-observations.json"
CFG_PATH = ROOT / "tasks" / "report-observation-config.json"
TZ = timezone(timedelta(hours=8))


def now_local_dt():
    return datetime.now(TZ)


def now_local():
    return now_local_dt().isoformat()


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


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_text(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def task_id_from_message_key(message_key):
    if not message_key:
        return ""
    return normalize_text(message_key).split("|", 1)[0]


def trim_observations(items, dedupe_mode="task", max_items=20, max_age_minutes=180):
    now_dt = now_local_dt()
    filtered = []
    for item in items or []:
        observed_at = parse_iso(item.get("observedAt"))
        if observed_at is None:
            filtered.append(item)
            continue
        age_minutes = (now_dt - observed_at).total_seconds() / 60.0
        if age_minutes <= max_age_minutes:
            filtered.append(item)

    latest = {}
    order = []
    for item in filtered:
        message_key = item.get("messageKey", "")
        dedupe_key = message_key if dedupe_mode == "message" else task_id_from_message_key(message_key)
        if dedupe_key not in latest:
            order.append(dedupe_key)
        latest[dedupe_key] = item
    filtered = [latest[key] for key in order if key in latest]

    if max_items and len(filtered) > max_items:
        filtered = filtered[-max_items:]
    return filtered


def parse_args():
    parser = argparse.ArgumentParser(description="Record a real success confirmation for pending sender delivery")
    parser.add_argument("--note", default="confirmed by explicit confirmation command")
    parser.add_argument("--source", default="manual_confirmation")
    return parser.parse_args()


def main():
    args = parse_args()
    state = load_json(STATE_PATH, {}) or {}
    observations = load_json(OBS_PATH, []) or []
    config = load_json(CFG_PATH, {}) or {}

    pending = state.get("pendingConfirmation") or {}
    payload = state.get("pendingToolPayload") or {}
    message_key = normalize_text(pending.get("messageKey") or payload.get("messageKey"))
    if not message_key:
        print(json.dumps({
            "written": False,
            "reason": "no pending confirmation to confirm",
            "observationCount": len(observations),
        }, ensure_ascii=False))
        return 0

    record = {
        "observedAt": now_local(),
        "messageKey": normalize_text(message_key),
        "status": "success",
        "note": args.note,
        "source": args.source,
    }
    observations.append(record)
    trimmed = trim_observations(
        observations,
        dedupe_mode=config.get("dedupeMode", "task"),
        max_items=config.get("maxItems", 20),
        max_age_minutes=config.get("maxAgeMinutes", 180),
    )
    save_json(OBS_PATH, trimmed)

    print(json.dumps({
        "written": True,
        "messageKey": message_key,
        "status": "success",
        "source": args.source,
        "observationCount": len(trimmed),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
