#!/usr/bin/env bash
set -u

status=0
xdo_pkg_config="missing"
xdo_fallback="missing"
xdo_status="blocked"

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

probe_xdo_fallback() {
  local dpkg_output=""
  local dpkg_status="unavailable"
  local header_status="missing"
  local library_status="missing"

  printf '==> xdo fallback probes\n'

  if command -v dpkg-query >/dev/null 2>&1; then
    if dpkg_output=$(dpkg-query -W -f='${Status} ${Version}\n' libxdo-dev 2>/dev/null); then
      dpkg_status="installed"
      printf 'INFO: libxdo-dev is installed according to dpkg-query (%s)\n' "$dpkg_output"
    else
      dpkg_status="missing"
      printf 'INFO: libxdo-dev is not installed according to dpkg-query\n'
    fi
  else
    printf 'INFO: dpkg-query is unavailable; skipping libxdo-dev package probe\n'
  fi

  if [ -f /usr/include/xdo.h ]; then
    header_status="present"
  fi
  printf 'INFO: /usr/include/xdo.h %s\n' "$header_status"

  if command -v ldconfig >/dev/null 2>&1; then
    if ldconfig -p 2>/dev/null | grep -q libxdo; then
      library_status="present"
    fi
    printf 'INFO: libxdo shared library %s via ldconfig\n' "$library_status"
  else
    printf 'INFO: ldconfig is unavailable; skipping libxdo shared library probe\n'
  fi

  if [ "$dpkg_status" = "installed" ] || {
    [ "$header_status" = "present" ] && [ "$library_status" = "present" ];
  }; then
    xdo_fallback="ok"
  else
    xdo_fallback="missing"
  fi

  printf 'xdo_fallback=%s\n\n' "$xdo_fallback"
}

probe_xdo() {
  printf '==> pkg-config xdo\n'
  if pkg-config --modversion xdo; then
    xdo_pkg_config="ok"
    printf 'PASS: xdo visible to pkg-config\n'
  else
    xdo_pkg_config="missing"
    printf 'WARN: xdo not visible to pkg-config\n'
  fi
  printf 'xdo_pkg_config=%s\n\n' "$xdo_pkg_config"

  probe_xdo_fallback

  if [ "$xdo_pkg_config" = "ok" ]; then
    xdo_status="ok"
  elif [ "$xdo_fallback" = "ok" ]; then
    xdo_status="warning"
    printf '%s\n\n' "pkg-config xdo module is missing, but libxdo-dev/header/library fallback is present; not a current Tauri build blocker."
  else
    xdo_status="blocked"
    status=1
  fi

  printf 'xdo_status=%s\n\n' "$xdo_status"
}

check_command "rustc" rustc -V
check_command "cargo" cargo -V
check_command "node" node -v
check_command "npm" npm -v
check_command "pkg-config" pkg-config --version

probe_pkg "webkit2gtk-4.1" || status=1
probe_pkg "openssl" || status=1
probe_xdo

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
