# openclaw-hard-delivery v0.1.0

Initial public release of `openclaw-hard-delivery`.

## Highlights
- Production-oriented hard-delivery runtime for OpenClaw report workflows
- Observation-driven reconciliation model
- Heartbeat-consumed scheduler observation inbox
- Reentry guards and terminal cleanup
- Single-command status, validation suite, and acceptance entrypoints
- Windows and macOS packaging baseline

## Included entrypoints
- `python tools/report_delivery_status.py`
- `python tools/run_report_delivery_acceptance.py`
- `python tools/validate_report_delivery_suite.py`

## Core delivery model
1. send or handoff
2. enter `pending_confirmation`
3. observe actual delivery from session side
4. reconcile from file evidence
5. cleanup into terminal success state

## Notes
This release is extracted from a real OpenClaw hardening effort and published as a reusable kit.
