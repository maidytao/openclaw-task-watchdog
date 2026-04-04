# openclaw-task-watchdog

**Stop long-running OpenClaw tasks from silently stalling in the middle.**

A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

`openclaw-task-watchdog` exists because long tasks often still look alive after they have already stalled, timed out, or stopped making real progress. This project makes that failure visible before humans mistake silence for progress.

---

## In one minute

### What it is
A file-backed watchdog runtime for OpenClaw long tasks.

### Why it exists
To prevent three expensive failure modes:
- silent stall
- fake progress
- silent interruption

### How it works
1. write explicit task state
2. allow uncertain middle states such as `pending_confirmation`
3. observe delivery or external evidence from the session side
4. reconcile from evidence
5. clean up into a clear terminal success state

### How to install

#### Windows
```powershell
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

#### macOS
```bash
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
bash ./scripts/install-macos.sh
```

### What to run first after install

#### Acceptance
```bash
python tools/run_report_delivery_acceptance.py
```

#### Status
```bash
python tools/report_delivery_status.py
```

#### Validation suite
```bash
python tools/validate_report_delivery_suite.py
```

If those are the only commands someone sees, they should still know how to install, verify, and inspect the system.

---

## What problem this solves

In real automation, long tasks frequently fail in ways that are hard to see:

- a task stalls but still looks "running"
- a send operation times out even though delivery may still happen
- the system stops making progress without declaring failure
- background loops re-enter and create duplicate or conflicting work
- operators discover the problem too late because the middle state was invisible

The real risk is not just failure.

The real risk is **silent failure that humans mistake for progress**.

---

## Installation details

This project is meant to be installed into an existing OpenClaw workspace.

### Requirements

Before installing, make sure you already have:

- OpenClaw installed and working
- a local OpenClaw workspace
  - Windows: `%USERPROFILE%\.openclaw\workspace`
  - macOS: `~/.openclaw/workspace`
- Python available in your shell
- permission to copy files into the OpenClaw workspace

### What the installer copies

The installer copies runtime files into your OpenClaw workspace, including:

- `tools/`
- `tasks/`
- `config/`
- `docs/OPERATE.md`

After install, the project is meant to run from inside the OpenClaw workspace where its file-backed state lives.

---

## First use after install

### 1. Run acceptance

Windows:
```powershell
python tools\run_report_delivery_acceptance.py
```

macOS:
```bash
python3 tools/run_report_delivery_acceptance.py
```

Expected result:
- acceptance verdict should be `PASS`

### 2. Check current status

Windows:
```powershell
python tools\report_delivery_status.py
```

macOS:
```bash
python3 tools/report_delivery_status.py
```

This tells you whether the watchdog runtime is currently healthy, including queue state, pending state, latest attempt status, dispatch reconciliation state, and latest validation evidence.

### 3. Run the validation suite when needed

Windows:
```powershell
python tools\validate_report_delivery_suite.py
```

macOS:
```bash
python3 tools/validate_report_delivery_suite.py
```

---

## What this project actually is

This is **not mainly a report sender**.

It is a **long-task watchdog runtime** for OpenClaw, with report delivery as the first hardened implementation.

The core idea is simple:

1. tasks must write state to disk
2. middle states must be explicit
3. timeout must not be confused with confirmed failure
4. success must be observation-backed
5. terminal cleanup must make the final state unambiguous
6. later loops must not re-enter completed work

---

## Why ordinary retries are not enough

A naive retry loop cannot answer the important questions:

- Did the task actually make progress?
- Did the message really fail, or only time out at the transport boundary?
- Is the task still active, or just stuck?
- Is the current state terminal, pending confirmation, or silently broken?
- Will the next scheduler cycle duplicate already-closed work?

This project adds the missing layer: **observable, reconciled, file-backed task supervision**.

---

## Current production path

The current production-ready path is a hardened OpenClaw report-delivery workflow with:

- file-backed sender state
- dispatch request planning
- scheduler observation bridge
- heartbeat-consumed inbox polling
- observation-driven reconcile
- terminal cleanup
- reentry guards
- validation, smoke, and acceptance tooling

That path proves the broader model: **long tasks can be supervised instead of merely launched**.

---

## Features

- **Long-task watchdog runtime** for OpenClaw workflows
- **Explicit middle states** such as `pending_confirmation` and `reconciled_success`
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
- validated runner + heartbeat closed-loop path

### macOS
- shell install baseline included
- repository layout prepared for launchd-style integration
- machine-specific OpenClaw adaptation may still be needed

---

## Repository layout

- `tools/` runtime, watchdog, operator, validation, and acceptance scripts
- `tasks/` task/runtime artifacts and example result files
- `config/` configuration templates
- `scripts/` install/uninstall/bootstrap helpers
- `docs/` architecture, operations, troubleshooting, quick start

---

## Healthy terminal state

A typical healthy terminal state looks like:

- queue is empty
- no `pendingToolPayload`
- no `pendingConfirmation`
- `lastError` is empty
- latest attempt is `success`
- `dispatchRequest.status` is `reconciled_success`
- acceptance verdict is `PASS`

---

## Scope note

This is **not** a generic messaging library.

It is an **OpenClaw-specific long-task supervision and delivery hardening kit** built around:

- OpenClaw workspace files
- session-side observation
- heartbeat polling
- file-backed reconciliation
- task/state/result artifacts

If you need a generic queue or transport abstraction, this repository is intentionally more opinionated than that.

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
