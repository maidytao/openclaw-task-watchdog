# Troubleshooting

## `pending_confirmation` is present
This can be expected immediately after runner-side execution. It becomes a problem only if it stays stuck and no session-side observation arrives.

## `sessions_send` timed out
Do not assume failure. Check file evidence and chat observation before marking the delivery failed.

## Queue does not clear
Inspect in this order:
1. `tasks/report-delivery-acceptance-result.json`
2. `tasks/report-delivery-suite-result.json`
3. `tasks/report-sender-state.json`
4. `tasks/report-queue.json`
5. `tasks/scheduler-observation-inbox.json`
6. `tasks/report-delivery-observations.json`

## Windows console mojibake
Ignore console mojibake when JSON files are correct. File contents are the ground truth.

## Scheduler runs but does not reach success
That can be normal. Runner-side automation may legitimately stop at `pending_confirmation`. Success closure may require session-side observation and reconcile.

## Acceptance fails
Run:
- `python tools/report_delivery_status.py`
- `python tools/validate_report_delivery_suite.py`
And inspect the result paths emitted by status.
