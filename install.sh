#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git+https://github.com/MaxxWasHere/matugenium.git"
APP_NAME="matugenium"

info() {
  printf "[matugenium-installer] %s\n" "$1"
}

warn() {
  printf "[matugenium-installer] WARNING: %s\n" "$1" >&2
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ensure_local_bin_path_hint() {
  local local_bin="$HOME/.local/bin"
  case ":${PATH:-}:" in
    *":$local_bin:"*) return 0 ;;
  esac

  warn "~/.local/bin is not currently in your PATH."
  warn "Add this to your shell config (~/.bashrc, ~/.zshrc, etc.):"
  printf '  export PATH="$HOME/.local/bin:$PATH"\n'
}

install_with_pipx() {
  info "Using pipx (preferred)."
  pipx ensurepath >/dev/null 2>&1 || true
  if pipx list 2>/dev/null | grep -q "$APP_NAME"; then
    info "Existing installation found; upgrading $APP_NAME."
    pipx upgrade "$APP_NAME" || pipx install "$REPO_URL"
  else
    pipx install "$REPO_URL"
  fi
}

install_with_pip_user() {
  info "Using python3 -m pip --user fallback."
  if ! python3 -m pip --version >/dev/null 2>&1; then
    warn "python3 pip is not available."
    warn "Please install pip (or pipx) and rerun this script."
    exit 1
  fi
  python3 -m pip install --user --upgrade "$REPO_URL"
}

verify_install() {
  if need_cmd "$APP_NAME"; then
    info "Install success."
    "$APP_NAME" --help >/dev/null 2>&1 || true
    info "Run: matugenium --gen-all  (or --gen <app>)"
    return 0
  fi

  warn "Install finished but '$APP_NAME' is not in PATH yet."
  ensure_local_bin_path_hint
  exit 1
}

main() {
  info "Installing matugenium..."

  if need_cmd pipx; then
    install_with_pipx
  else
    warn "pipx not found; falling back to user pip install."
    install_with_pip_user
  fi

  verify_install
}

main "$@"
