# Desktop Status

## Status

`scaffolded_blocked`

The web GUI is stable enough to wrap, but this machine does not currently have the Rust/Cargo prerequisites required to run or build a Tauri 2 desktop shell.

## Checked On

2026-04-23

## Prerequisite Check

```bash
command -v node
command -v npm
command -v rustc
command -v cargo
```

Observed:

- `node`: present
- `npm`: present
- `rustc`: missing
- `cargo`: missing

## Scaffold Location

```text
desktop/tauri/
```

The scaffold intentionally contains documentation rather than an unverified generated Rust project. Once Rust/Cargo are available, the wrapper should be created here and point to the already-built web GUI.

## Intended Wrapper Boundary

- Frontend: `apps/gui-web`
- Web build output: `apps/gui-web/dist`
- Backend communication: local FastAPI at `http://127.0.0.1:8000`
- No business logic should move into Tauri.
- No GPU or provider-backed long-running job should be started by desktop packaging.

## Next Commands After Installing Prerequisites

```bash
rustc --version
cargo --version
cd apps/gui-web
npm run build
```

Then scaffold Tauri 2 under `desktop/tauri/` and configure it to wrap `../../apps/gui-web/dist` for build output and the Vite dev server during development.
