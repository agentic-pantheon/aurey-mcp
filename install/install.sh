#!/usr/bin/env sh
# Aurey Wallet MCP — install CLI from PyPI (no secrets; run aurey-setup separately).
set -eu

AUREY_VERSION="${AUREY_VERSION:-}"
AUREY_INSTALL_METHOD="${AUREY_INSTALL_METHOD:-auto}"
AUREY_PACKAGE="aurey-wallet-mcp[hermes]"
DOCS_URL="${AUREY_DOCS_URL:-https://agentic-pantheon.github.io/aurey-mcp/install.html}"

die() {
  echo "aurey-install: $*" >&2
  exit 1
}

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found. Install Python 3.12+."
  fi
  pyver="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  major="${pyver%%.*}"
  minor="${pyver#*.}"
  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 12 ]; }; then
    die "Python 3.12+ required (found $pyver)."
  fi
}

pkg_spec() {
  if [ -n "$AUREY_VERSION" ]; then
    printf '%s==%s' "$AUREY_PACKAGE" "$AUREY_VERSION"
  else
    printf '%s' "$AUREY_PACKAGE"
  fi
}

install_uv() {
  spec="$(pkg_spec)"
  if ! command -v uv >/dev/null 2>&1; then
    return 1
  fi
  echo "→ Installing $spec with uv tool …"
  uv tool install --force "$spec"
  return 0
}

install_pip() {
  spec="$(pkg_spec)"
  echo "→ Installing $spec with pip …"
  if command -v pipx >/dev/null 2>&1; then
    pipx install --force "$spec"
    return 0
  fi
  python3 -m pip install --user --upgrade "$spec"
}

main() {
  check_python
  method="$AUREY_INSTALL_METHOD"
  if [ "$method" = "auto" ]; then
    if install_uv; then
      :
    else
      install_pip
    fi
  elif [ "$method" = "uv" ]; then
    install_uv || die "uv not on PATH"
  elif [ "$method" = "pip" ]; then
    install_pip
  else
    die "Unknown AUREY_INSTALL_METHOD=$method (use auto, uv, or pip)"
  fi

  if ! command -v aurey-setup >/dev/null 2>&1; then
    die "aurey-setup not on PATH. Add Python user bin or uv tool dir to PATH."
  fi

  echo ""
  echo "✓ Aurey Wallet MCP installed."
  echo ""
  echo "Next (in this terminal — do not paste 1ck_ or ocv_ keys into chat):"
  echo "  aurey-setup --host <hermes|cursor|claude|openclaw>"
  echo ""
  echo "Examples:"
  echo "  aurey-setup --host cursor"
  echo "  aurey-setup --host hermes"
  echo ""
  echo "Host guides: ${DOCS_URL%.html}/install/cursor.html (and hermes, claude, openclaw)"
  echo "Full guide: $DOCS_URL"
}

main "$@"
