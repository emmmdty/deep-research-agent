# Tauri Desktop Wrapper

Status: `READY_FOR_TAURI_BUILD`

This directory contains the Tauri 2 desktop wrapper around the existing local web GUI. The desktop shell wraps `apps/gui-web`; it does not move research runtime, provider, audit, benchmark, or artifact logic into Rust.

## Structure

```text
desktop/tauri/
  package.json
  package-lock.json
  src-tauri/
    Cargo.toml
    Cargo.lock
    tauri.conf.json
    build.rs
    capabilities/default.json
    icons/icon.png
    src/lib.rs
    src/main.rs
```

## Wiring

- Development URL: `http://127.0.0.1:5173`
- `beforeDevCommand`: `npm --prefix ../../apps/gui-web run dev -- --port 5173`
- `beforeBuildCommand`: `npm --prefix ../../apps/gui-web run build`
- `frontendDist`: `../../../apps/gui-web/dist`
- Local API expected by the GUI: `http://127.0.0.1:8000`

## Commands

From the repository root:

```bash
npm_config_cache=/tmp/npm-cache npm install --prefix desktop/tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri
```

For a bounded dev wiring check that does not open a desktop window:

```bash
timeout 180s env CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run tauri --prefix desktop/tauri -- dev --no-watch --runner true
```

For an interactive desktop dev run:

```bash
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:dev --prefix desktop/tauri
```

The `CARGO_HOME` and `npm_config_cache` overrides are only needed when the user-level cache directories are read-only.

## Last Verified

2026-04-23:

- `./scripts/check_tauri_env.sh` -> pass, `TAURI_ENV_STATUS=ok`
- `npm_config_cache=/tmp/npm-cache npm test --prefix apps/gui-web` -> pass, `4` files and `6` tests
- `npm_config_cache=/tmp/npm-cache npm run build --prefix apps/gui-web` -> pass
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri` -> pass
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri` -> pass
- bounded `tauri dev --no-watch --runner true` -> pass; Vite started at `http://127.0.0.1:5173/`
