# openclaw-hard-delivery

A production-oriented hard-delivery runtime for OpenClaw report workflows.

`openclaw-hard-delivery` packages a real hardened delivery pattern for OpenClaw: **send -> pending confirmation -> observed delivery -> reconcile -> cleanup**.

It exists for one specific reason: in real OpenClaw report delivery, a `sessions_send` timeout does **not** always mean delivery failed. If you treat timeout as hard failure, you can create duplicate sends, broken state, and false-negative delivery alerts. This toolkit implements the safer model and wraps it with status, validation, acceptance, and operator docs.

---

## Why this exists

In practical OpenClaw automation, delivery has a messy middle:

- a tool-side send can time out
- the chat message may still arrive successfully
- the system needs an explicit `pending_confirmation` state
- delivery should close only after session-side observation
- background loops must not re-enter after success

This repository turns those lessons into a reusable kit.

## Core model

The delivery lifecycle used here is:

1. prepare/send or handoff
2. enter `pending_confirmation`
3. observe actual delivery from the session side
4. reconcile from evidence
5. clean protocol artifacts into terminal state

That model is backed by file evidence rather than fragile console assumptions.

---

## Features

- **Hard-delivery runtime** for OpenClaw report workflows
- **Observation-driven reconciliation** instead of timeout-as-failure
- **Heartbeat-consumed observation inbox** for session-side closure
- **Reentry guards and terminal cleanup** to prevent duplicate work
- **Single-command status entrypoint**
- **Single-command acceptance entrypoint**
- **Validation suite** covering runner, heartbeat, and smoke flows
- **Windows + macOS packaging baseline**

---

## Entry points

### Status
```bash
python tools/report_delivery_status.py
```

### Acceptance
```bash
python tools/run_report_delivery_acceptance.py
```

### Validation suite
```bash
python tools/validate_report_delivery_suite.py
```

---

## Platform support

### Windows
- Scheduled Task driven runner flow
- batch/bootstrap helpers
- validation and acceptance flow verified during extraction

### macOS
- shell install baseline included
- repository layout prepared for launchd-style integration
- additional machine-specific adaptation may still be needed depending on local OpenClaw layout

---

## Repository layout

- `tools/` runtime, operator, validation, and acceptance scripts
- `tasks/` task/runtime artifacts and example result files
- `config/` configuration templates
- `scripts/` install/uninstall/bootstrap helpers
- `docs/` architecture, operations, troubleshooting, quick start

---

## Quick start

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
python tools\run_report_delivery_acceptance.py
python tools\report_delivery_status.py
```

### macOS
```bash
bash ./scripts/install-macos.sh
python3 tools/run_report_delivery_acceptance.py
python3 tools/report_delivery_status.py
```

---

## When the system is healthy

Typical healthy terminal state looks like:

- queue is empty
- no `pendingToolPayload`
- no `pendingConfirmation`
- `lastError` is empty
- latest attempt is `success`
- `dispatchRequest.status` is `reconciled_success`
- acceptance verdict is `PASS`

---

## Important scope note

This is **not** a generic messaging library.

It is an **OpenClaw-specific delivery hardening kit** built around:

- OpenClaw workspace files
- session-side observation
- heartbeat polling
- file-backed reconciliation
- task/state/result artifacts

If you want a generic library, this repo is intentionally more opinionated than that.

---

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/OPERATE.md`
- `docs/TROUBLESHOOTING.md`
- `docs/QUICKSTART.md`
- `docs/PUBLISHING-NOTES.md`

---

## License

MIT
