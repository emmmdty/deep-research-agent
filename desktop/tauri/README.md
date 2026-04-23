# Tauri Desktop Scaffold

Status: `scaffolded_blocked`

This directory is reserved for the Tauri 2 desktop wrapper around the local web GUI.

## Current Blocker

Desktop build prerequisites are missing on this machine:

- `rustc`: missing
- `cargo`: missing

The web GUI remains the primary runnable surface. Do not force a desktop build until Rust/Cargo are installed and visible in PATH.

## Intended Shape

- Use `apps/gui-web` as the frontend source.
- Use `apps/gui-web/dist` as the desktop build artifact.
- Keep all research runtime behavior behind the local FastAPI/CLI surfaces.
- Do not move provider, benchmark, audit, or artifact logic into Rust/Tauri.

## Validation Before Continuing

```bash
rustc --version
cargo --version
npm --prefix ../../apps/gui-web run build
```

If these pass, generate or complete the Tauri 2 project in this directory and add a desktop smoke check to `docs/gui/DESKTOP_STATUS.md`.
