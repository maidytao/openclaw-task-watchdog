import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\.openclaw\workspace")
CFG_PATH = ROOT / "tasks" / "report-sender-config.json"
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


def normalize_text(value):
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def message_key(item):
    msg = item.get("message") or {}
    return "|".join([
        normalize_text(item.get("taskId", "")),
        normalize_text(item.get("status", "")),
        normalize_text(msg.get("blocker", "")),
        normalize_text(msg.get("nextAction", "")),
        normalize_text(msg.get("nextUpdateBy", "")),
    ])


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def payload_freshness(item):
    msg = item.get("message") or {}
    next_update_by = parse_iso(msg.get("nextUpdateBy"))
    now = now_local_dt()
    if not next_update_by:
        return {
            "nextUpdateBy": msg.get("nextUpdateBy"),
            "isExpired": False,
            "ageSeconds": None,
        }
    delta = now - next_update_by
    age_seconds = int(delta.total_seconds())
    return {
        "nextUpdateBy": msg.get("nextUpdateBy"),
        "isExpired": age_seconds > 0,
        "ageSeconds": age_seconds,
    }


def refresh_item_if_stale(item, cfg):
    freshness = payload_freshness(item)
    if not freshness.get("isExpired"):
        return item, False

    msg = dict(item.get("message") or {})
    refresh_minutes = int(cfg.get("refreshMinutes", 10))
    refreshed_until = (now_local_dt() + timedelta(minutes=refresh_minutes)).isoformat()
    msg["nextUpdateBy"] = refreshed_until

    refreshed = dict(item)
    refreshed["message"] = msg
    refreshed["refreshedAt"] = now_local()
    refreshed["refreshReason"] = "pending-payload-expired"
    return refreshed, True


def build_delivery_text(item):
    msg = item.get("message") or {}
    return "\n".join([
        "[[reply_to_current]] 任务状态通知",
        f"状态：{msg.get('status', '')}",
        f"交付物：{msg.get('deliverable', '')}",
        f"阻塞：{msg.get('blocker', '')}",
        f"下一步：{msg.get('nextAction', '')}",
        f"下次更新：{msg.get('nextUpdateBy', '')}",
    ])


def build_tool_payload(item, session_key=None):
    freshness = payload_freshness(item)
    return {
        "sessionKey": session_key,
        "message": build_delivery_text(item),
        "messageKey": message_key(item),
        "taskId": item.get("taskId"),
        "createdAt": now_local(),
        "freshness": freshness,
    }


def build_delivery_record(item, dry_run=True, delivery_mode="dry-run", session_key=None):
    text = build_delivery_text(item)
    return {
        "sentAt": now_local(),
        "taskId": item.get("taskId"),
        "status": item.get("status"),
        "dryRun": dry_run,
        "deliveryMode": delivery_mode,
        "sessionKey": session_key,
        "messageKey": message_key(item),
        "text": text,
        "toolPayload": build_tool_payload(item, session_key) if session_key else None,
    }


def is_same_message_active(state, key):
    if not key:
        return False
    if normalize_text((state.get("lastDeliveredPayloadKey") or "").split("|", 2)[1] if "|" in (state.get("lastDeliveredPayloadKey") or "") else "") == key:
        return True
    pending = state.get("pendingConfirmation") or {}
    payload = state.get("pendingToolPayload") or {}
    dispatch = state.get("dispatchRequest") or {}
    live_plan = state.get("liveSendPlan") or {}
    for candidate in [
        pending.get("messageKey"),
        payload.get("messageKey"),
        dispatch.get("messageKey"),
        live_plan.get("messageKey"),
    ]:
        if normalize_text(candidate) == key:
            return True
    for attempt in reversed(list(state.get("toolDeliveryAttempts", []) or [])):
        if normalize_text(attempt.get("messageKey")) != key:
            continue
        if attempt.get("status") in {"success", "dispatched", "timeout_pending_confirmation", "pending_confirmation"}:
            return True
    return False


def deliver_item(item, cfg):
    target = cfg.get("target", {}) or {}
    dry_run = bool(cfg.get("dryRun", True))
    text = build_delivery_text(item)
    session_key = target.get("sessionKey")

    if dry_run:
        return {
            "ok": True,
            "dryRun": True,
            "deliveryMode": "dry-run",
            "text": text,
            "sessionKey": session_key,
            "messageKey": message_key(item),
        }

    if not session_key:
        return {
            "ok": False,
            "dryRun": False,
            "deliveryMode": "session",
            "error": "missing target.sessionKey",
            "messageKey": message_key(item),
        }

    return {
        "ok": False,
        "dryRun": False,
        "deliveryMode": "session",
        "error": "real session delivery must be invoked by OpenClaw tool wrapper, not direct script execution",
        "text": text,
        "sessionKey": session_key,
        "messageKey": message_key(item),
        "toolPayload": build_tool_payload(item, session_key),
    }


def main():
    cfg = load_json(CFG_PATH, {}) or {}
    if not cfg.get("enabled", False):
        print("DISABLED")
        return 0

    queue_path = ROOT / cfg.get("queueFile", "tasks/report-queue.json")
    state_path = ROOT / cfg.get("stateFile", "tasks/report-sender-state.json")
    batch_size = int(cfg.get("batchSize", 10))

    queue = load_json(queue_path, []) or []
    state = load_json(state_path, {}) or {}
    sent_keys = set(state.get("sentKeys", []) or [])
    delivered = list(state.get("delivered", []) or [])

    normalized_queue = []
    refreshed_items = []
    for item in queue:
        refreshed_item, changed = refresh_item_if_stale(item, cfg)
        normalized_queue.append(refreshed_item)
        if changed:
            refreshed_items.append({
                "taskId": refreshed_item.get("taskId"),
                "nextUpdateBy": (refreshed_item.get("message") or {}).get("nextUpdateBy"),
                "refreshReason": refreshed_item.get("refreshReason"),
            })
    queue = normalized_queue

    pending = []
    skipped_existing = []
    for item in queue:
        key = message_key(item)
        if key in sent_keys:
            continue
        if is_same_message_active(state, key):
            skipped_existing.append({
                "taskId": item.get("taskId"),
                "messageKey": key,
                "reason": "existing_delivery_state",
            })
            continue
        pending.append((key, item))

    processed = []
    kept_queue = []
    last_error = ""
    pending_tool_payload = None

    for index, (key, item) in enumerate(pending):
        if index >= batch_size:
            kept_queue.append(item)
            continue

        result = deliver_item(item, cfg)
        if result.get("ok"):
            delivered.append(build_delivery_record(
                item,
                dry_run=result.get("dryRun", True),
                delivery_mode=result.get("deliveryMode", "dry-run"),
                session_key=result.get("sessionKey"),
            ))
            sent_keys.add(key)
            processed.append({
                "taskId": item.get("taskId"),
                "status": item.get("status"),
                "dryRun": result.get("dryRun", True),
                "deliveryMode": result.get("deliveryMode", "dry-run"),
                "sessionKey": result.get("sessionKey"),
                "messageKey": result.get("messageKey"),
            })
        else:
            kept_queue.append(item)
            last_error = result.get("error", "delivery failed")
            pending_tool_payload = result.get("toolPayload")

    for item in queue:
        key = message_key(item)
        if key not in sent_keys and all(message_key(keep) != key for keep in kept_queue):
            kept_queue.append(item)

    deduped_kept = []
    seen_keys = set()
    for item in kept_queue:
        key = message_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_kept.append(item)

    save_json(queue_path, deduped_kept)
    state["lastRunAt"] = now_local()
    state["lastSentAt"] = now_local() if processed else state.get("lastSentAt")
    state["sentKeys"] = sorted(sent_keys)
    state["delivered"] = delivered[-50:]
    state["lastError"] = last_error
    state["lastProcessedCount"] = len(processed)
    state["refreshedItems"] = refreshed_items[-20:]
    if pending_tool_payload:
        state["pendingToolPayload"] = pending_tool_payload
    elif not deduped_kept:
        state.pop("pendingToolPayload", None)
    save_json(state_path, state)

    print(json.dumps({
        "processed": processed,
        "remainingQueue": len(deduped_kept),
        "dryRun": bool(cfg.get("dryRun", True)),
        "lastProcessedCount": len(processed),
        "lastError": last_error,
        "pendingToolPayload": state.get("pendingToolPayload"),
        "refreshedItems": refreshed_items,
        "skippedExisting": skipped_existing,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
