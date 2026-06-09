"""Shared Aurey MCP install helpers (all hosts)."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Literal

SERVER_NAME = "aurey-wallet"
VAULT_API_KEY_ENV = "AUREY_ONECLAW_VAULT_API_KEY"
LEGACY_VAULT_API_KEY_ENV = "AUREY_ONECLAW_BOOTSTRAP_API_KEY"
DEFAULT_ALCHEMY_VAULT_PATH = "api-keys/alchemy"
DEFAULT_LIFI_VAULT_PATH = "api-keys/lifi"
LIFI_EARN_QUICKSTART_URL = "https://docs.li.fi/earn/quickstart"
HUMAN_API_KEY_ENV = "AUREY_ONECLAW_HUMAN_API_KEY"

LIFI_SETUP_HINT = (
    "LiFi API key (optional — Enter to skip):\n"
    "  • Used for LiFi Earn vault discovery (earn_list_vaults, APY/TVL, Composer flags) "
    "and higher-rate LiFi swap/Composer quotes.\n"
    "  • Basic swaps may work without a key; the Earn Data API (earn.li.fi) requires "
    "the x-lifi-api-key header.\n"
    f"  • Get a key: {LIFI_EARN_QUICKSTART_URL} "
    "(sign up at https://portal.li.fi/signup → create an API key).\n"
    f"  • When provided, stored in your 1Claw vault at {DEFAULT_LIFI_VAULT_PATH!r}."
)

REQUIRED_MCP_ENV_KEYS = (
    "AUREY_ONECLAW_VAULT_ID",
    VAULT_API_KEY_ENV,
    "AUREY_ONECLAW_AGENT_ID",
)

McpHost = Literal["hermes", "cursor", "claude", "openclaw"]


def aurey_home() -> Path:
    return Path.home() / ".aurey"


def mcp_env_path() -> Path:
    return aurey_home() / "mcp.env"


def mcp_wrapper_path() -> Path:
    return aurey_home() / "run-aurey-wallet-mcp.sh"


INSTALL_PACKAGE_HINT = (
    "Install aurey-wallet-mcp first: "
    "curl -fsSL https://agentic-pantheon.github.io/aurey-mcp/install.sh | bash "
    "or: pip install aurey-wallet-mcp "
    "(add [hermes] for Hermes YAML tooling only)"
)


def dev_repo_root(path: str | None) -> Path | None:
    """Return repo root when ``path`` or cwd contains ``pyproject.toml``."""

    candidates: list[Path] = []
    if path:
        candidates.append(Path(path).expanduser().resolve())
    else:
        candidates.append(Path.cwd().resolve())
    for root in candidates:
        if (root / "pyproject.toml").is_file():
            return root
    return None


def resolve_mcp_command(repo: str | None = None) -> Path:
    """Locate ``aurey-wallet-mcp``: PATH (PyPI) then dev ``.venv`` in repo/cwd."""

    found = shutil.which("aurey-wallet-mcp")
    if found:
        return Path(found).resolve()
    root = dev_repo_root(repo)
    if root is not None:
        bin_path = root / ".venv" / "bin" / "aurey-wallet-mcp"
        if bin_path.is_file():
            return bin_path.resolve()
    raise SystemExit(INSTALL_PACKAGE_HINT)


def maybe_dev_sync(repo: str | None, *, skip_sync: bool) -> None:
    if skip_sync:
        return
    root = dev_repo_root(repo)
    if root is not None:
        run_uv_sync(root)


def run_uv_sync(repo: Path) -> None:
    if shutil.which("uv") is None:
        raise SystemExit("`uv` not on PATH. Install uv or run sync manually.")
    subprocess.run(["uv", "sync", "--group", "dev"], cwd=repo, check=True)


def secrets_from_ids(
    *,
    vault_id: str,
    agent_id: str,
    vault_api_key: str,
) -> dict[str, str]:
    return {
        "AUREY_ONECLAW_VAULT_ID": vault_id.strip(),
        "AUREY_ONECLAW_AGENT_ID": agent_id.strip(),
        VAULT_API_KEY_ENV: vault_api_key.strip(),
    }


def upsert_dotenv(env_path: Path, updates: dict[str, str], *, comment: str) -> list[str]:
    """Merge KEY=value into a dotenv file; return keys written."""

    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    index: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, _ = stripped.partition("=")
        index[key.strip()] = i

    written: list[str] = []
    added_section = False
    for key, value in updates.items():
        if not key or value is None:
            continue
        val = value.replace("\n", "").replace("\r", "")
        entry = f"{key}={val}"
        if key in index:
            lines[index[key]] = entry
        else:
            if not added_section:
                if lines and lines[-1].strip():
                    lines.append("")
                lines.append(f"# {comment}")
                added_section = True
            lines.append(entry)
            index[key] = len(lines) - 1
        written.append(key)

    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return written


def write_mcp_env(secrets: dict[str, str], *, path: Path | None = None) -> Path:
    """Write shared MCP credentials (chmod 600)."""

    env_path = path or mcp_env_path()
    upsert_dotenv(
        env_path,
        {k: secrets[k] for k in REQUIRED_MCP_ENV_KEYS if secrets.get(k, "").strip()},
        comment="Aurey Wallet MCP credentials (aurey-setup)",
    )
    try:
        env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return env_path


def load_mcp_env(path: Path | None = None) -> dict[str, str]:
    env_path = path or mcp_env_path()
    if not env_path.is_file():
        raise SystemExit(f"Missing {env_path}. Run aurey-setup without --skip-provision first.")
    out: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        out[key.strip()] = val.strip()
    return out


def write_mcp_wrapper(*, binary: Path, env_path: Path | None = None) -> Path:
    """Shell wrapper: source mcp.env then exec MCP binary (keeps secrets out of host JSON)."""

    wrapper = mcp_wrapper_path()
    env_file = (env_path or mcp_env_path()).expanduser()
    bin_abs = binary.resolve()
    aurey_home().mkdir(parents=True, exist_ok=True)
    body = (
        "#!/usr/bin/env sh\n"
        "set -e\n"
        "set -a\n"
        f'. "{env_file}"\n'
        "set +a\n"
        f'exec "{bin_abs}"\n'
    )
    wrapper.write_text(body, encoding="utf-8")
    wrapper.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return wrapper


def ensure_aurey_toml_alchemy_path(
    config_path: Path,
    *,
    secret_path: str = DEFAULT_ALCHEMY_VAULT_PATH,
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    body = ""
    if config_path.is_file():
        body = config_path.read_text(encoding="utf-8")
    marker = "[providers]"
    line = f'alchemy_secret_path = "{secret_path}"'
    if "alchemy_secret_path" in body:
        return
    if marker in body:
        new_body = body.replace(marker, f"{marker}\n{line}", 1)
    else:
        new_body = (body.rstrip() + "\n\n" if body.strip() else "") + f"{marker}\n{line}\n"
    config_path.write_text(new_body, encoding="utf-8")


def ensure_aurey_toml_lifi_path(
    config_path: Path,
    *,
    secret_path: str = DEFAULT_LIFI_VAULT_PATH,
) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    body = ""
    if config_path.is_file():
        body = config_path.read_text(encoding="utf-8")
    marker = "[providers]"
    line = f'lifi_api_secret_path = "{secret_path}"'
    if "lifi_api_secret_path" in body:
        return
    if marker in body:
        new_body = body.replace(marker, f"{marker}\n{line}", 1)
    else:
        new_body = (body.rstrip() + "\n\n" if body.strip() else "") + f"{marker}\n{line}\n"
    config_path.write_text(new_body, encoding="utf-8")


def smoke_test(binary: Path, env: dict[str, str]) -> None:
    proc = subprocess.run(
        [str(binary)],
        env={**os.environ, **{k: v for k, v in env.items() if v}},
        capture_output=True,
        text=True,
        timeout=8,
        input="",
    )
    if proc.returncode == 0:
        return
    err = (proc.stderr or proc.stdout or "").strip()
    if "Bootstrap failed" in err:
        raise SystemExit(err.splitlines()[-1] if err else "Bootstrap failed.")
    if proc.returncode != 0 and err:
        raise SystemExit(err)


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def save_json_object(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def missing_required(secrets: dict[str, str]) -> list[str]:
    return [k for k in REQUIRED_MCP_ENV_KEYS if not secrets.get(k, "").strip()]


def host_reload_hint(host: McpHost) -> str:
    hints = {
        "hermes": "In Hermes chat: /reload-mcp · Terminal: hermes mcp test aurey-wallet",
        "cursor": "Restart Cursor or reload MCP from Cursor Settings → MCP",
        "claude": "Quit and reopen Claude Desktop (MCP loads at startup)",
        "openclaw": "Restart the OpenClaw gateway after config change",
    }
    return hints[host]
