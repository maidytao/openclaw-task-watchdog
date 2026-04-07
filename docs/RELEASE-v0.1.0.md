# openclaw-task-watchdog v0.1.0

Initial public release of `openclaw-task-watchdog`.

## What it is

A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

This release packages a practical OpenClaw supervision model for long tasks: make middle states visible, let uncertain delivery remain uncertain until observed, reconcile from evidence, and clean up into a clear terminal state.

## Highlights

- Production-oriented watchdog model for long-running OpenClaw tasks
- Detection of silent interruption and no-progress states through explicit file-backed runtime state
- Observation-driven reconciliation instead of timeout-as-failure
- Heartbeat-consumed scheduler observation inbox
- Reentry guards and terminal cleanup
- Single-command status, validation suite, and acceptance entrypoints
- Windows and macOS packaging baseline

## Post-release expansion now included in the repository

After the initial public release, the repository was extended with a broader resumable-task runtime and resilience verification layer.

### Newly added runtime capabilities
- `task_runner.py` for resumable task progression and restart control
- `task_executor.py` for concrete next-action execution
- `task_reporter.py` for richer reporting flow support
- `sync_report_delivery_terminal_state.py` for handling real-world acceptable terminal boundary states such as `pending_confirmation`
- `normalize_completed_task_state.py` for cleanup of dirty completed-state history

### Newly added validation and resilience tooling
- `validate_resumable_system.py` as a unified system-level validator
- `validate_runner_reentry_guard.py`
- `validate_runner_stability.py`
- `validate_scheduler_real_run.py`
- `validate_terminal_state_sync.py`
- `run_resilience_chaos_tests.py`
- `run_resilience_chaos_tests_round2.py`
- `run_resilience_chaos_tests_round3.py`
- `run_full_resilience_acceptance.py`

### Newly added task/runtime config and shell entrypoints
- `tasks/heartbeat-config.json`
- `tasks/runner-config.json`
- `tasks/executor-config.json`
- `tasks/task-registry.json`
- `tasks/task-types.json`
- `tasks/executor-actions.json`
- `tasks/heartbeat-runner.bat`
- `tasks/runner.bat`
- `tasks/executor.bat`

### Included verification artifacts
- unified resumable-system validation report
- runner reentry/stability reports
- scheduler real-run report
- terminal sync report
- completed-task normalization result
- three rounds of chaos / resilience test reports
- final resilience rating
- full resilience acceptance report

## What this expansion proves

The project now demonstrates more than report-delivery supervision.

It shows that an OpenClaw long task can:
- persist state
- survive interruption
- be restarted under rules
- execute concrete next actions
- reconcile from evidence
- normalize into a clean terminal state
- withstand active breakage testing
- produce a final resilience report

## Core model

1. prepare work or handoff
2. enter `pending_confirmation`
3. observe actual delivery or external evidence from the session side
4. reconcile from file evidence
5. cleanup into terminal success state

## Install and verify

After installing into an OpenClaw workspace, the main entrypoints are:

- `python tools/report_delivery_status.py`
- `python tools/run_report_delivery_acceptance.py`
- `python tools/validate_report_delivery_suite.py`

## Why it matters

Long-running automation often fails in the middle while still looking alive. This project exists to make that failure visible before humans mistake silence for progress.
