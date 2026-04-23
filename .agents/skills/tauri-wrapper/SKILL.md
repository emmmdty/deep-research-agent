---
name: tauri-wrapper
description: Use this skill when packaging the local web GUI into a desktop shell using Tauri 2. Use it only after the web GUI is already stable. If Tauri prerequisites are missing, scaffold and document the blocker instead of forcing the build.
---

# tauri-wrapper

## Purpose
Wrap the existing local web GUI as a desktop application without changing the backend architecture.

## Preconditions
- web GUI exists and builds
- desktop packaging is in-scope for the current phase

## Steps
1. Check whether Rust/Cargo/Tauri prerequisites are available.
2. If available, scaffold the Tauri 2 wrapper around the web frontend build.
3. Keep backend interaction through the existing local API unless a minimal bridge is clearly needed.
4. If prerequisites are missing, leave a scaffold + docs + exact blocker report.

## Avoid
- rewriting the app into a Rust-first desktop app
- replacing the existing backend with Tauri-side business logic
- blocking the whole GUI run on missing desktop prerequisites
