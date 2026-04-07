# openclaw-task-watchdog

> New here? Start with [`START-HERE.md`](./START-HERE.md).

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

The current production path now has two layers:

### 1. Hardened report-delivery watchdog path
- file-backed sender state
- dispatch request planning
- scheduler observation bridge
- heartbeat-consumed inbox polling
- observation-driven reconcile
- terminal cleanup
- reentry guards
- validation, smoke, and acceptance tooling

### 2. General resumable-task supervision path
- file-backed `current-task` ledger
- heartbeat watchdog for overdue or silent work
- runner-driven restart / restart-circuit-breaker logic
- executor-driven concrete next-action execution
- completed-state normalization from verifiable evidence
- terminal state sync for real-world boundary states like `pending_confirmation`
- multi-round resilience / chaos testing
- full one-command acceptance report

That means the repository is no longer only a report-delivery watchdog demo.

It now also contains a more general **resumable long-task runtime** for OpenClaw.

---

## What's new in v0.2.0

The repository now includes a broader resumable-task supervision layer on top of the original report-delivery watchdog path.

### Newly added runtime pieces
- `task_runner.py`
- `task_executor.py`
- `task_reporter.py`
- `normalize_completed_task_state.py`
- `sync_report_delivery_terminal_state.py`

### Newly added resilience tooling
- unified resumable-system validation
- three rounds of chaos / fault-injection testing
- one-command full resilience acceptance
- final resilience rating and included report artifacts

If you only remember one thing from this update, remember this:

**the project now proves not only that delivery can be supervised, but that resumable long tasks can be persisted, restarted, validated, stress-tested, and closed cleanly.**

---

## Features

- **Long-task watchdog runtime** for OpenClaw workflows
- **Explicit middle states** such as `pending_confirmation` and `reconciled_success`
- **Observation-driven reconciliation** instead of timeout-as-failure
- **Heartbeat-consumed observation inbox** for session-side closure
- **Reentry guards and terminal cleanup** to prevent duplicate work
- **Resumable task runner** for stalled or restart-required work
- **Task executor** for concrete next-step advancement
- **Completed-state normalization** from verifiable evidence
- **Resilience / chaos test suite** with multi-round fault injection
- **Full acceptance report** for end-to-end resilience verification
- **Single-command status entrypoint**
- **Single-command acceptance entrypoint**
- **Validation suite** covering runner, heartbeat, and smoke flows
- **Windows + macOS packaging baseline**

---

## Entry points

### Report-delivery status
```bash
python tools/report_delivery_status.py
```

### Report-delivery acceptance
```bash
python tools/run_report_delivery_acceptance.py
```

### Report-delivery validation suite
```bash
python tools/validate_report_delivery_suite.py
```

### Full resumable-system acceptance
```bash
python tools/run_full_resilience_acceptance.py
```

### Unified resumable-system validation
```bash
python tools/validate_resumable_system.py
```

### Chaos / resilience rounds
```bash
python tools/run_resilience_chaos_tests.py
python tools/run_resilience_chaos_tests_round2.py
python tools/run_resilience_chaos_tests_round3.py
```

---

## Architecture overview

At a high level, the runtime works like this:

1. a task writes explicit state to disk
2. heartbeat logic checks whether it is overdue or silent
3. runner logic decides whether to continue, restart, or open a circuit breaker
4. executor logic performs a concrete next action
5. observation or completion evidence is collected
6. terminal sync / normalization cleans the task into a clear completed state
7. validation and resilience scripts verify that the whole chain survives real failure modes

In practice, the repository currently contains two connected supervision paths:

- **report-delivery watchdog path**
- **general resumable-task runtime path**

The report-delivery path is the original hardened implementation.

The resumable-task path is the broader expansion that proves the model can supervise more than just message delivery.

---

## How to run resilience tests

### Round 1
```bash
python tools/run_resilience_chaos_tests.py
```

### Round 2
```bash
python tools/run_resilience_chaos_tests_round2.py
```

### Round 3
```bash
python tools/run_resilience_chaos_tests_round3.py
```

### Full acceptance
```bash
python tools/run_full_resilience_acceptance.py
```

### Unified validation
```bash
python tools/validate_resumable_system.py
```

---

## How to read the included reports

The repository contains both runtime config and generated evidence.

### Most important result files
- `tasks/example-resumable-system-test-report.json`
- `tasks/example-resilience-chaos-report.json`
- `tasks/example-resilience-chaos-report-round2.json`
- `tasks/example-resilience-chaos-report-round3.json`
- `tasks/example-resilience-final-rating.json`
- `tasks/example-full-resilience-acceptance-report.json`

### What each one tells you
- **`example-resumable-system-test-report.json`**: whether the core resumable supervision chain is healthy
- **`example-resilience-chaos-report*.json`**: what happened in each active breakage round
- **`example-resilience-final-rating.json`**: condensed final resilience score / conclusion
- **`example-full-resilience-acceptance-report.json`**: end-to-end acceptance summary for the expanded runtime

If you want a fast read:
1. start with `tasks/example-resilience-final-rating.json`
2. then open `tasks/example-full-resilience-acceptance-report.json`
3. then inspect individual round reports only if you want test-by-test detail

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
- `tasks/` task/runtime templates plus published example result files
- `config/` configuration templates
- `scripts/` install/uninstall/bootstrap helpers
- `docs/` architecture, operations, troubleshooting, quick start

Public repo note:
- machine-local runtime state should stay in the local OpenClaw workspace
- committed JSON reports in `tasks/` are published example evidence, not the only intended runtime store
- see `tasks/README-reports.md` for report-file guidance

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
- `docs/PUBLIC-REPO-AUDIT-v0.2.0.md`

---

## License

MIT
