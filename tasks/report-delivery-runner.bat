@echo off
setlocal
cd /d C:\Users\Administrator\.openclaw\workspace
python tools\task_report_sender.py
if errorlevel 1 exit /b %errorlevel%
python tools\task_report_sender_dispatcher.py
if errorlevel 1 exit /b %errorlevel%
python tools\task_report_sender_mark_pending.py
if errorlevel 1 exit /b %errorlevel%
python tools\prepare_scheduler_observation_bridge.py
if errorlevel 1 exit /b %errorlevel%
python tools\task_report_sender_reconcile.py --note "runner reconcile without synthetic success observation"
if errorlevel 1 exit /b %errorlevel%
python tools\cleanup_stale_report_protocol.py
exit /b %errorlevel%
