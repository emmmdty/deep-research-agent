#!/usr/bin/env bash
set -u

status=0

check_command() {
  local name="$1"
  shift

  printf '==> %s\n' "$name"
  if "$@"; then
    printf 'PASS: %s\n\n' "$name"
  else
    printf 'FAIL: %s\n\n' "$name"
    status=1
  fi
}

probe_pkg() {
  local pkg="$1"
  printf '==> pkg-config %s\n' "$pkg"
  if pkg-config --modversion "$pkg"; then
    printf 'PASS: %s visible to pkg-config\n\n' "$pkg"
  else
    printf 'FAIL: %s not visible to pkg-config\n\n' "$pkg"
    return 1
  fi
}

check_command "rustc" rustc -V
check_command "cargo" cargo -V
check_command "node" node -v
check_command "npm" npm -v
check_command "pkg-config" pkg-config --version

probe_pkg "webkit2gtk-4.1" || status=1
probe_pkg "openssl" || status=1

if ! probe_pkg "xdo"; then
  if dpkg -s libxdo-dev >/dev/null 2>&1; then
    printf 'WARN: xdo.pc is not visible, but libxdo-dev is installed according to dpkg.\n\n'
  else
    status=1
  fi
fi

if probe_pkg "ayatana-appindicator3-0.1"; then
  :
elif probe_pkg "appindicator3-0.1"; then
  :
else
  status=1
fi

probe_pkg "gtk+-3.0" || status=1
probe_pkg "javascriptcoregtk-4.1" || status=1
probe_pkg "libsoup-3.0" || status=1
probe_pkg "librsvg-2.0" || status=1

if [ "$status" -eq 0 ]; then
  printf 'TAURI_ENV_STATUS=ok\n'
else
  printf 'TAURI_ENV_STATUS=blocked\n'
fi

exit "$status"
