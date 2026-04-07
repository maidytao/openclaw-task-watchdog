# openclaw-task-watchdog v0.2.0

Resumable runtime and resilience expansion release.

## Summary

This release moves `openclaw-task-watchdog` beyond a report-delivery watchdog baseline.

The repository now includes a broader **resumable long-task runtime** for OpenClaw, together with unified validation, active breakage testing, and final resilience reporting.

## What is new

### Resumable task runtime
- Added `task_runner.py` for resumable task progression and restart handling
- Added `task_executor.py` for concrete next-action execution
- Added `task_reporter.py` for richer reporting flow support
- Added completed-state normalization and terminal-state synchronization logic

### Stronger validation
- Added unified validator: `tools/validate_resumable_system.py`
- Added targeted validators for:
  - runner reentry guard
  - runner stability
  - scheduler real-run behavior
  - terminal state sync

### Resilience / chaos testing
- Added three rounds of active breakage testing:
  - `run_resilience_chaos_tests.py`
  - `run_resilience_chaos_tests_round2.py`
  - `run_resilience_chaos_tests_round3.py`
- Added one-command end-to-end acceptance:
  - `run_full_resilience_acceptance.py`

### Runtime config and entrypoints
- Added heartbeat / runner / executor config files
- Added runner / heartbeat / executor batch entrypoints
- Added resumable-task runtime task registry and task-type definitions

## Included reports

This release includes generated verification artifacts, including:
- unified resumable-system test report
- runner reentry guard result
- runner stability result
- scheduler real-run result
- terminal-state-sync result
- completed-task normalization result
- three chaos resilience round reports
- final resilience rating
- full resilience acceptance report

## Why this release matters

Long-running automation often fails in the middle while still looking alive.

This release demonstrates that an OpenClaw long task can now:
- persist explicit task state
- survive interruption
- restart under controlled rules
- execute concrete next actions
- reconcile from external evidence
- normalize into a clean terminal state
- withstand active fault injection
- produce a final resilience report

## Recommended entrypoints

### Report-delivery baseline
```bash
python tools/report_delivery_status.py
python tools/run_report_delivery_acceptance.py
python tools/validate_report_delivery_suite.py
```

### Resumable runtime validation
```bash
python tools/validate_resumable_system.py
```

### Full resilience acceptance
```bash
python tools/run_full_resilience_acceptance.py
```

### Chaos rounds
```bash
python tools/run_resilience_chaos_tests.py
python tools/run_resilience_chaos_tests_round2.py
python tools/run_resilience_chaos_tests_round3.py
```

## Suggested release title

`v0.2.0 - Resumable runtime and resilience expansion`

## Suggested short release text

Adds a resumable long-task runtime for OpenClaw with runner/executor support, unified validation, active chaos testing, and final resilience reporting.
