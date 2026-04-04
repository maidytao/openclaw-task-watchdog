# Operations

## Fast status
```bash
python tools/report_delivery_status.py
```

Healthy signs:
- `systemHealthy: true`
- queue length `0`
- no pending payload
- no pending confirmation
- last error empty
- `dispatchRequestStatus: reconciled_success`

## Full acceptance
```bash
python tools/run_report_delivery_acceptance.py
```

Passing signs:
- `passed: true`
- `verdict: PASS`
- `failures: []`

## Validation suite
```bash
python tools/validate_report_delivery_suite.py
```

Runs:
- runner inbox stability
- heartbeat scheduler observation
- runner + heartbeat smoke
