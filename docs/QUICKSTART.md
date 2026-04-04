# Quick Start

This project is for OpenClaw users who want a watchdog layer for long-running tasks.

Its goal is to stop long tasks from silently stalling in the middle without anyone noticing.

The current production path is a hardened report-delivery workflow, but the install, validation, and status steps below are also the best way to understand how the watchdog runtime works.

---

## Before you start

Make sure you already have:

- OpenClaw installed and working
- a local OpenClaw workspace at:
  - Windows: `C:\Users\<you>\.openclaw\workspace`
  - macOS: `~/.openclaw/workspace`
- Python available in your shell
- permission to copy files into your OpenClaw workspace

If your OpenClaw workspace does not exist yet, create or initialize OpenClaw first.

---

## What the installer copies

The installer copies these parts into your OpenClaw workspace:

- `tools/` runtime, watchdog, validation, and acceptance scripts
- `tasks/` runtime/task state files and validation result files
- `config/` template config files
- `docs/OPERATE.md` operator guide

This means the project becomes usable from inside the OpenClaw workspace where the runtime expects to read and write state.

---

## Windows install

### 1. Clone the repository

```powershell
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
```

### 2. Run the installer

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1
```

What this does:

- finds your OpenClaw workspace under `%USERPROFILE%\.openclaw\workspace`
- copies the runtime files into that workspace
- prints the next recommended verification step

### 3. Run acceptance

```powershell
python tools\run_report_delivery_acceptance.py
```

Expected outcome:

- acceptance file is written
- verdict should be `PASS`

### 4. Check live status

```powershell
python tools\report_delivery_status.py
```

This shows whether the watchdog runtime is currently healthy, including:

- queue length
- pending state
- latest attempt status
- dispatch reconciliation status
- latest heartbeat and poll results
- validation suite summary

---

## macOS install

### 1. Clone the repository

```bash
git clone https://github.com/maidytao/openclaw-task-watchdog.git
cd openclaw-task-watchdog
```

### 2. Run the installer

```bash
bash ./scripts/install-macos.sh
```

What this does:

- finds your OpenClaw workspace under `~/.openclaw/workspace`
- copies the runtime files into that workspace
- prints the next recommended verification step

### 3. Run acceptance

```bash
python3 tools/run_report_delivery_acceptance.py
```

Expected outcome:

- acceptance file is written
- verdict should be `PASS`

### 4. Check live status

```bash
python3 tools/report_delivery_status.py
```

---

## Day-1 usage

After installation, the three most important commands are:

### See whether the system is healthy
```bash
python tools/report_delivery_status.py
```

### Run the full validation suite
```bash
python tools/validate_report_delivery_suite.py
```

### Run the final acceptance check
```bash
python tools/run_report_delivery_acceptance.py
```

---

## How to think about this project

If you are new to the repository, the simplest mental model is:

1. a long task starts
2. the runtime records explicit state
3. if delivery or progress enters an uncertain middle state, it becomes visible
4. heartbeat/session-side observation helps close that uncertainty
5. reconcile + cleanup convert that into a clean terminal state

This is why the project is called a watchdog runtime: it is there to make silent interruption visible before humans mistake silence for progress.
