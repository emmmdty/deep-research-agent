# Tauri Desktop Wrapper

Status: `READY_FOR_TAURI_BUILD`

This directory contains the Tauri 2 desktop wrapper around the existing local web GUI. The desktop shell wraps `apps/gui-web`; it does not move research runtime, provider, audit, benchmark, or artifact logic into Rust.

## Structure

```text
apps/desktop-tauri/
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
- `beforeDevCommand`: `npm --prefix ../../gui-web run dev -- --port 5173`
- `beforeBuildCommand`: `npm --prefix ../../gui-web run build`
- `frontendDist`: `../../gui-web/dist`
- Local API expected by the GUI: `http://127.0.0.1:8000`

## Commands

From the repository root:

```bash
npm_config_cache=/tmp/npm-cache npm install --prefix apps/desktop-tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix apps/desktop-tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix apps/desktop-tauri
```

For a bounded dev wiring check that does not open a desktop window:

```bash
timeout 180s env CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run tauri --prefix apps/desktop-tauri -- dev --no-watch --runner true
```

For an interactive desktop dev run:

```bash
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:dev --prefix apps/desktop-tauri
```

The `CARGO_HOME` and `npm_config_cache` overrides are only needed when the user-level cache directories are read-only.

`pkg-config --modversion xdo` may fail on this environment because `xdo.pc` is not visible. `./scripts/check_tauri_env.sh` now distinguishes `xdo_pkg_config`, `xdo_fallback`, and `xdo_status` so the missing `xdo.pc` file is not treated as a blocker when `libxdo-dev`, `/usr/include/xdo.h`, and the runtime `libxdo` library are already present.

## Last Verified

2026-04-25:

- `./scripts/check_tauri_env.sh` -> pass, `xdo_pkg_config=missing`, `xdo_fallback=ok`, `xdo_status=warning`, `TAURI_ENV_STATUS=ok`
- `npm_config_cache=/tmp/npm-cache npm test --prefix apps/gui-web` -> pass, `4` files and `6` tests
- `npm_config_cache=/tmp/npm-cache npm run lint --prefix apps/gui-web` -> pass
- `npm_config_cache=/tmp/npm-cache npm run build --prefix apps/gui-web` -> pass
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix apps/desktop-tauri` -> pass
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix apps/desktop-tauri` -> pass
- bounded `tauri dev --no-watch --runner true` -> pass; Vite started at `http://127.0.0.1:5173/`

If a future Tauri build fails with real `xdo` or linker errors, revisit the exact Linux dependency state at that point instead of assuming the current fallback evidence is still sufficient.
