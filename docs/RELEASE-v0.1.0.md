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
