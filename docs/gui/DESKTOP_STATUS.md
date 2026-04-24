# Desktop Status

## Status

`READY_FOR_TAURI_BUILD`

The Tauri desktop layer is now a repo-local Tauri 2 wrapper around the existing web GUI. Bounded dev wiring and no-bundle release build validation passed on 2026-04-23.

## Checked On

2026-04-23

## Prerequisite Check

```bash
rustc -V
cargo -V
node -v
npm -v
./scripts/check_tauri_env.sh
```

Observed:

- `rustc`: `rustc 1.95.0 (59807616e 2026-04-14)`
- `cargo`: `cargo 1.95.0 (f2d3ce0bd 2026-03-21)`
- `node`: `v24.14.0`
- `npm`: `11.12.0`
- `webkit2gtk-4.1`: `2.50.4`
- `openssl`: `3.0.2`
- `ayatana-appindicator3-0.1`: `0.5.90`
- `gtk+-3.0`: `3.24.33`
- `javascriptcoregtk-4.1`: `2.50.4`
- `libsoup-3.0`: `3.0.7`
- `librsvg-2.0`: `2.52.5`
- `xdo`: `pkg-config` probe failed, but `libxdo-dev 1:3.20160805.1-4` is installed and the Tauri build passed.

## Scaffold Location

```text
desktop/tauri/
```

The scaffold now contains:

- repo-local npm package and lockfile for `@tauri-apps/cli`
- `src-tauri/Cargo.toml` and `Cargo.lock`
- `src-tauri/tauri.conf.json`
- minimal Rust entrypoints under `src-tauri/src/`
- Tauri capability file under `src-tauri/capabilities/`
- app icon under `src-tauri/icons/icon.png`

## Wrapper Boundary

- Frontend source: `apps/gui-web`
- Dev URL: `http://127.0.0.1:5173`
- Build output: `apps/gui-web/dist`
- Backend communication: local FastAPI at `http://127.0.0.1:8000`
- Runtime, provider, audit, benchmark, and artifact logic stay outside Rust/Tauri.
- Desktop packaging must not start GPU work or provider-backed long-running jobs.

## Verification Commands

Use temporary caches if the user-level npm/Cargo cache directories are read-only:

```bash
npm_config_cache=/tmp/npm-cache npm install --prefix apps/gui-web
npm_config_cache=/tmp/npm-cache npm test --prefix apps/gui-web
npm_config_cache=/tmp/npm-cache npm run build --prefix apps/gui-web
npm_config_cache=/tmp/npm-cache npm install --prefix desktop/tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri
CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri
timeout 180s env CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run tauri --prefix desktop/tauri -- dev --no-watch --runner true
```

Observed outcomes:

- Frontend install: pass, dependencies up to date.
- Frontend tests: pass, `4` files and `6` tests.
- Frontend build: pass, Vite output under `apps/gui-web/dist`.
- Desktop install: pass, `@tauri-apps/cli@2.10.1`.
- Tauri info: pass, WebKitGTK/Rust/Cargo detected, `devUrl` and `frontendDist` recognized.
- Tauri no-bundle build: pass, release binary built at `desktop/tauri/src-tauri/target/release/deep-research-agent-desktop`.
- Bounded dev wiring: pass, Vite started on `http://127.0.0.1:5173/` and `--runner true` avoided opening a desktop window.

## Notes

- Do not use `sudo` for this workflow.
- Do not install system packages from this repo run.
- If user-level cache directories become writable later, the temporary `npm_config_cache` and `CARGO_HOME` overrides are optional.
- Full installer/AppImage bundling was not required for this unblock run; the validated command is `tauri build --no-bundle`.
