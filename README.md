# openclaw-task-watchdog

**Make silent long-task interruption visible before humans mistake silence for progress.**

A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

`openclaw-task-watchdog` exists to solve a more important problem than message delivery: **long-running tasks often look alive after they have already stalled, timed out, or stopped making real progress**. This project makes those failures visible.

It turns long-task execution into a file-backed, heartbeat-supervised, observation-driven workflow with explicit intermediate states, reconciliation, terminal cleanup, and acceptance checks.

The repository currently ships a hardened report-delivery pipeline as its first production path, but the underlying purpose is broader: **prevent silent interruption, detect no-progress states early, and ensure that "done" means observed and reconciled — not guessed.**

---

## What you get

This project gives long-running OpenClaw tasks a watchdog layer that can:

- detect when work stops making real progress
- preserve explicit middle states instead of hiding them
- keep timeout from being confused with confirmed failure
- wait for observed evidence before closing success
- prevent reentry after terminal completion
- expose status, validation, and acceptance with single commands

If someone scans only this section, they should already understand the point: **this is for preventing long tasks from silently dying in the middle without anyone noticing.**

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

## Installation

This project is meant to be installed into an existing OpenClaw workspace.

### Requirements

Before installing, make sure you already have:

- OpenClaw installed and working
- a local OpenClaw workspace
  - Windows: `%USERPROFILE%\.openclaw\workspace`
  - macOS: `~/.openclaw/workspace`
- Python available in your shell
- permission to copy files into the OpenClaw workspace

### Windows

```powershell
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

### macOS

```bash
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
bash ./scripts/install-macos.sh
```

### What the installer does

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

## Watchdog model

The hardened lifecycle used in this repository is:

1. prepare work or handoff
2. enter `pending_confirmation`
3. observe actual delivery or external evidence from the session side
4. reconcile from evidence
5. clean protocol artifacts into terminal success state

That model is intentionally built around persisted JSON evidence instead of fragile console assumptions.

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
