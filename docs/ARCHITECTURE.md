# Architecture

## Core principle
`send != delivered`

`sessions_send` may time out while the message still arrives in chat. Therefore the runtime must model delivery as an observation-driven state machine instead of a single send-success boolean.

## State model
Typical flow:
- pending payload prepared
- dispatch request created
- pending confirmation recorded
- session-side observation written
- reconcile closes queue/state
- cleanup marks protocol artifacts terminal

Important statuses used by the toolkit include:
- `pending_confirmation`
- `dispatched`
- `timeout_pending_confirmation`
- `success`
- `reconciled_success`

## Why file evidence matters
Windows console output can show mojibake or misleading intermediate text. The toolkit treats JSON files as the source of truth.

## Runtime split
### Runner side
Responsible for:
- sender
- dispatcher planning
- pending confirmation recording
- bridge/inbox preparation
- reconcile attempt
- cleanup

### Session side
Responsible for:
- polling scheduler observation inbox
- writing success observation once delivery is observed
- reconciling and cleaning up terminal state

## Design requirements learned from production hardening
- idempotent re-entry guards
- file-backed evidence
- explicit intermediate states
- separate status / suite / acceptance entrypoints
- operator documentation
