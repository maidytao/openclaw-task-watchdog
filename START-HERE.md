# START HERE

If you are new to this repository, read this file first.

`openclaw-task-watchdog` is a watchdog runtime for long-running OpenClaw tasks.

Its job is to stop long tasks from silently stalling, disappearing, or faking progress without operators noticing.

---

## What this project is for

Use this project when you need:

- explicit task state on disk
- visible middle states such as `pending_confirmation`
- observation before claiming success
- reconciliation from evidence
- cleanup into a clear terminal state
- validation and acceptance commands that tell you whether the system is actually healthy

The current production path in this repository is a hardened OpenClaw report-delivery workflow, but the bigger purpose is long-task supervision.

---

## What to do first

### 1. Install into an OpenClaw workspace

#### Windows
```powershell
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

#### macOS
```bash
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
bash ./scripts/install-macos.sh
```

---

### 2. Run acceptance

Windows:
```powershell
python tools\run_report_delivery_acceptance.py
```

macOS:
```bash
python3 tools/run_report_delivery_acceptance.py
```

Expected result:
- verdict should be `PASS`

---

### 3. Check current status

Windows:
```powershell
python tools\report_delivery_status.py
```

macOS:
```bash
python3 tools/report_delivery_status.py
```

This shows whether the current runtime state is healthy.

---

### 4. Run the full validation suite when needed

Windows:
```powershell
python tools\validate_report_delivery_suite.py
```

macOS:
```bash
python3 tools/validate_report_delivery_suite.py
```

---

## What healthy looks like

A healthy terminal state usually means:

- queue is empty
- no `pendingToolPayload`
- no `pendingConfirmation`
- `lastError` is empty
- latest attempt is `success`
- `dispatchRequest.status` is `reconciled_success`
- acceptance verdict is `PASS`

---

## If you want more detail next

Read these in order:

1. `README.md`
2. `docs/QUICKSTART.md`
3. `docs/OPERATE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/TROUBLESHOOTING.md`
