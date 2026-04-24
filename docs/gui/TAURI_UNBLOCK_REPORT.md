## Summary

The desktop layer is now a real Tauri 2 wrapper around the existing web GUI instead of a documentation-only scaffold. The repo-local Tauri config, Rust crate, npm CLI dependency, icon asset, and diagnostics are present, and bounded Tauri dev/build validation passed on this machine when npm and Cargo caches were redirected to `/tmp`.

The default user-level npm and Cargo caches under `/home/tjk` are read-only in this environment. That is an environment cache-location issue, not a missing Linux package or broken Tauri config.

## Checked files

- `AGENTS.md`
- `README.md`
- `docs/gui/README.md`
- `docs/gui/DEMO_FLOW.md`
- `docs/gui/DESKTOP_STATUS.md`
- `docs/gui/TAURI_UNBLOCK_REPORT.md`
- `desktop/tauri/README.md`
- `desktop/tauri/package.json`
- `desktop/tauri/package-lock.json`
- `desktop/tauri/src-tauri/Cargo.toml`
- `desktop/tauri/src-tauri/tauri.conf.json`
- `desktop/tauri/src-tauri/src/lib.rs`
- `desktop/tauri/src-tauri/src/main.rs`
- `desktop/tauri/src-tauri/capabilities/default.json`
- `scripts/check_tauri_env.sh`
- `.agent/gui_app/STATUS.md`
- `.agent/STATUS.md`
- `apps/gui-web/package.json`
- `apps/gui-web/vite.config.ts`

## Toolchain findings

- `rustc -V` -> `rustc 1.95.0 (59807616e 2026-04-14)`
- `cargo -V` -> `cargo 1.95.0 (f2d3ce0bd 2026-03-21)`
- `node -v` -> `v24.14.0`
- `npm -v` -> `11.12.0`
- `pkg-config --version` -> `0.29.2`

Rust, Cargo, Node, npm, and pkg-config are available.

## Linux prerequisite findings

- `pkg-config --modversion webkit2gtk-4.1` -> `2.50.4`
- `pkg-config --modversion openssl` -> `3.0.2`
- `pkg-config --modversion xdo` -> failed because `xdo.pc` is not visible
- `dpkg -l libxdo-dev` -> `libxdo-dev 1:3.20160805.1-4` installed
- `pkg-config --modversion ayatana-appindicator3-0.1` -> `0.5.90`
- `pkg-config --modversion gtk+-3.0` -> `3.24.33`
- `pkg-config --modversion javascriptcoregtk-4.1` -> `2.50.4`
- `pkg-config --modversion libsoup-3.0` -> `3.0.7`
- `pkg-config --modversion librsvg-2.0` -> `2.52.5`

The required Linux development packages are present for the bounded Tauri build. The only probe anomaly is missing `xdo.pc`; the package itself is installed and the Tauri build completed.

## Tauri CLI findings

- `npm ls @tauri-apps/cli --prefix apps/gui-web` -> no web-app-local Tauri CLI dependency.
- `npm_config_cache=/tmp/npm-cache npm view @tauri-apps/cli version` -> `2.10.1`.
- `npm_config_cache=/tmp/npm-cache npm install --prefix desktop/tauri` -> added repo-local desktop CLI dependency.
- `npm ls @tauri-apps/cli --prefix desktop/tauri` -> `@tauri-apps/cli@2.10.1`.

The Tauri CLI is now repo-local to `desktop/tauri`, not coupled to the web GUI package.

## Frontend/Tauri wiring findings

- Frontend dev server: `apps/gui-web` Vite server on `http://127.0.0.1:5173`.
- Frontend build output: `apps/gui-web/dist`.
- Tauri `beforeDevCommand`: `npm --prefix ../../apps/gui-web run dev -- --port 5173`.
- Tauri `devUrl`: `http://127.0.0.1:5173`.
- Tauri `beforeBuildCommand`: `npm --prefix ../../apps/gui-web run build`.
- Tauri `frontendDist`: `../../../apps/gui-web/dist`.
- Tauri app boundary: Rust shell only; runtime, provider, audit, benchmark, and artifact logic remain behind the existing local API/CLI surfaces.

`tauri info` recognized the configured `devUrl` and `frontendDist`, and `tauri build --no-bundle` consumed the web build output successfully.

## Commands executed and outcomes

- `git worktree add /tmp/tauri-desktop-unblock-attempt-1 -b codex/tauri-desktop-unblock/attempt-1 main` -> failed; Git could not create nested branch refs.
- `git worktree add /tmp/tauri-desktop-unblock-attempt-1 -b tauri-desktop-unblock-attempt-1 main` -> failed; `.git/refs/heads/*.lock` is on a read-only filesystem.
- `rustc -V`, `cargo -V`, `node -v`, `npm -v` -> pass.
- `pkg-config --modversion webkit2gtk-4.1` -> pass.
- `pkg-config --modversion openssl` -> pass.
- `pkg-config --modversion xdo` -> probe failed, but `libxdo-dev` is installed.
- `pkg-config --modversion ayatana-appindicator3-0.1 || pkg-config --modversion appindicator3-0.1` -> pass via Ayatana.
- `./scripts/check_tauri_env.sh` -> pass with `TAURI_ENV_STATUS=ok`.
- `npm view @tauri-apps/cli version` -> failed because `/home/tjk/.npm` cache is read-only.
- `npm_config_cache=/tmp/npm-cache npm view @tauri-apps/cli version` -> pass, `2.10.1`.
- `npm_config_cache=/tmp/npm-cache npm install --prefix apps/gui-web` -> pass, up to date, zero vulnerabilities.
- `npm_config_cache=/tmp/npm-cache npm test --prefix apps/gui-web` -> pass, `4` files and `6` tests.
- `npm_config_cache=/tmp/npm-cache npm run build --prefix apps/gui-web` -> pass, Vite output under `apps/gui-web/dist`.
- `npm_config_cache=/tmp/npm-cache npm install --prefix desktop/tauri` -> pass, local Tauri CLI installed.
- `npm ls @tauri-apps/cli --prefix desktop/tauri` -> pass, `@tauri-apps/cli@2.10.1`.
- `npm_config_cache=/tmp/npm-cache npm run desktop:info --prefix desktop/tauri` -> pass; Tauri environment and app wiring detected.
- `npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri` -> failed because `/home/tjk/.cargo` registry cache is read-only.
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri` -> failed once because `src-tauri/icons/icon.png` was missing.
- `CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run desktop:build --prefix desktop/tauri` after adding the icon -> pass; built `desktop/tauri/src-tauri/target/release/deep-research-agent-desktop`.
- `timeout 180s env CARGO_HOME=/tmp/cargo-home npm_config_cache=/tmp/npm-cache npm run tauri --prefix desktop/tauri -- dev --no-watch --runner true` -> pass; `beforeDevCommand` started Vite on `http://127.0.0.1:5173/` and the runner avoided opening a desktop window.
- `git add ...` -> failed because `.git/index.lock` is on a read-only filesystem.

## Repo-local fixes applied

- Added `desktop/tauri/package.json` and `desktop/tauri/package-lock.json` with repo-local `@tauri-apps/cli@2.10.1`.
- Added `desktop/tauri/src-tauri/` with minimal Tauri 2 Rust crate, config, capability, and opener plugin wiring.
- Added `desktop/tauri/src-tauri/icons/icon.png` so Tauri context generation can complete.
- Added `scripts/check_tauri_env.sh` for repeatable non-sudo Linux prerequisite checks.
- Updated `.gitignore` to ignore Rust/Tauri generated `target/` and `src-tauri/gen/` outputs.
- Updated desktop and GUI documentation/status files to reflect the verified desktop state.

## Remaining blockers

There are no remaining blockers for bounded Tauri dev/build validation on this machine.

Operational notes:

- Use `npm_config_cache=/tmp/npm-cache` if `/home/tjk/.npm` remains read-only.
- Use `CARGO_HOME=/tmp/cargo-home` if `/home/tjk/.cargo` remains read-only.
- Git metadata was read-only during this run, so creating a maintenance branch/worktree and committing the verified repo changes failed.

## Final verdict

READY_FOR_TAURI_BUILD

## Exact next manual action (if still blocked)

None. For repeatability in this WSL environment, run desktop commands with `npm_config_cache=/tmp/npm-cache` and `CARGO_HOME=/tmp/cargo-home` when user-level caches are read-only.
