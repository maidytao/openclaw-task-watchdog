# Repo short texts

## One-line description
A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

## Short pitch
openclaw-task-watchdog helps OpenClaw operators detect silent task interruption, no-progress states, and false-alive runs before humans mistake silence for progress.

## Two-sentence pitch
This repository turns long-running OpenClaw work into a supervised, file-backed, observation-driven execution loop with heartbeat polling, reconciliation, and terminal cleanup. Its first production path is hardened report delivery, but the real purpose is broader: prevent silent interruption and make long-task failure visible early.

## Plain-language explanation
If a long task gets stuck halfway, times out in the middle, or stops producing real output while still looking alive, this project is meant to catch that and make it visible. It gives long OpenClaw tasks a watchdog layer so they can be checked, observed, reconciled, and cleanly closed instead of silently drifting.
