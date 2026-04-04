# openclaw-task-watchdog v0.1.0

Initial public release of `openclaw-task-watchdog`.

## What it is

A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

## Highlights

- Production-oriented long-task watchdog model for OpenClaw
- Observation-driven reconciliation instead of timeout-as-failure
- Heartbeat-consumed scheduler observation inbox
- Reentry guards and terminal cleanup
- Single-command status, validation suite, and acceptance entrypoints
- Windows and macOS packaging baseline

## Core model

1. prepare work or handoff
2. enter `pending_confirmation`
3. observe actual delivery from the session side
4. reconcile from file evidence
5. cleanup into terminal success state

## Entry points

- `python tools/report_delivery_status.py`
- `python tools/run_report_delivery_acceptance.py`
- `python tools/validate_report_delivery_suite.py`
