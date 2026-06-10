#!/usr/bin/env python3
"""Build miniapp and sync into package static/portfolio for wheel distribution."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINIAPP = ROOT / "miniapp"
DIST = MINIAPP / "dist"
TARGET = ROOT / "src" / "aurey_wallet_mcp" / "static" / "portfolio"


def main() -> None:
    if not (MINIAPP / "package.json").is_file():
        raise SystemExit(f"Missing {MINIAPP / 'package.json'}")

    subprocess.run(["npm", "ci"], cwd=MINIAPP, check=True)
    subprocess.run(["npm", "run", "build"], cwd=MINIAPP, check=True)

    if not (DIST / "index.html").is_file():
        raise SystemExit(f"Build did not produce {DIST / 'index.html'}")

    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DIST, TARGET)
    print(f"Synced portfolio UI to {TARGET}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc) from exc
