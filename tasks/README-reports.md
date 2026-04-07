# Report files in this repository

This repository intentionally includes a small set of generated result files.

They are included as **published example evidence**, not as live runtime state that should be edited in place during normal operation.

## What these reports are for

These files help readers understand:
- what the validation outputs look like
- what the resilience test outputs look like
- what a final acceptance summary looks like

## What they are not for

They are **not** meant to be the only runtime storage for your own deployment.

In a real installation, your local OpenClaw workspace will generate its own task state, queue state, runner state, executor state, and validation outputs.

## Recommended practice for users

- Treat the committed report JSON files as examples / published evidence
- Generate fresh reports in your own local workspace when validating your own installation
- Avoid committing machine-specific runtime state back into the repository unless you are intentionally publishing a new example result set

## Files most readers should start with

- `tasks/example-resilience-final-rating.json`
- `tasks/example-full-resilience-acceptance-report.json`
- `tasks/example-resumable-system-test-report.json`
