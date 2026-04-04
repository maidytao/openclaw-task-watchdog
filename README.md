# openclaw-hard-delivery

Cross-platform hard-delivery toolkit for OpenClaw report delivery pipelines.

This project packages the practical lessons from a long real-world hardening session into a reusable deployment kit for **Windows** and **macOS**.

## What it solves

OpenClaw report delivery should not treat `sessions_send` timeout as final failure. Real delivery may still succeed, so the safe model is:

1. send or handoff
2. enter `pending_confirmation`
3. observe actual delivery from the session side
4. reconcile to success
5. cleanup protocol artifacts

This repository packages that workflow with:
- runtime scripts
- status and acceptance entrypoints
- regression validators
- Windows and macOS install/bootstrap scripts
- operations documentation

## Included entrypoints

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

## Platforms
- Windows: supported via Scheduled Task + batch/bootstrap helpers
- macOS: supported via launchd bootstrap template + shell installer

## Repository layout
- `tools/` runtime, validation, and operator entrypoints
- `tasks/` result and state examples/templates
- `config/` config templates
- `scripts/` install/bootstrap helpers
- `docs/` architecture, operations, troubleshooting

## Install

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

### macOS
```bash
bash ./scripts/install-macos.sh
```

## Operator flow
1. Install toolkit into your OpenClaw workspace
2. Run acceptance
3. Check status
4. Let heartbeat/session-side poller close pending deliveries

## Important note
This project is not a generic messaging library. It is an OpenClaw-specific delivery hardening kit built around:
- OpenClaw workspace files
- session-side observation
- heartbeat polling
- reconciliation from file evidence

## License
MIT
