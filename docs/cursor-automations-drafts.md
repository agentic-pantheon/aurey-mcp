# Cursor Automations drafts — aurey-mcp

Prefill payloads for the five maintainer automations. Each block matches what was sent to the Automations editor via `prefillWorkflowData`. Save each in the editor after review.

**Repo:** `agentic-pantheon/aurey-mcp` · **Default branch:** `main`

---

## 1. PR quality gate — aurey-mcp

**Trigger:** Pull request opened and code pushed on PR (repo `agentic-pantheon/aurey-mcp`)  
**Tools:** Comment on PRs

```json
{
  "name": "PR quality gate — aurey-mcp",
  "description": "Run pytest and ruff on PR branches and comment results.",
  "workflow": {
    "triggers": [
      {
        "git": {
          "pullRequest": {
            "action": "GIT_PULL_REQUEST_ACTION_OPENED",
            "repos": ["agentic-pantheon/aurey-mcp"],
            "ignoreDraftPrs": true
          }
        }
      },
      {
        "git": {
          "pullRequest": {
            "action": "GIT_PULL_REQUEST_ACTION_PUSHED",
            "repos": ["agentic-pantheon/aurey-mcp"],
            "ignoreDraftPrs": true
          }
        }
      }
    ],
    "actions": [{ "prComment": {} }],
    "prompts": [
      {
        "prompt": "You were triggered by a pull request on agentic-pantheon/aurey-mcp. Use the cloud agent checkout for the PR branch from the trigger context (do not merge).\n\n1. Sync dev dependencies: `uv sync --group dev`\n2. Run `uv run pytest` and `uv run ruff check .`\n3. Post a single PR comment summarizing pass/fail for both checks, aligned with docs/releasing.md (pytest must be green before release).\n\nIf either check fails, list the most important errors (file/line or test name) and suggest fixes. If both pass, give a short confirmation. Do not merge or approve the PR."
      }
    ],
    "model": "",
    "agentOptions": { "skipInstall": false },
    "memoryEnabled": false
  }
}
```

---

## 2. PR secrets & wallet safety — aurey-mcp

**Trigger:** Pull request opened (same repo)  
**Tools:** Comment on PRs

```json
{
  "name": "PR secrets & wallet safety — aurey-mcp",
  "description": "Review PR diffs for leaked secrets and wallet/MCP safety regressions.",
  "workflow": {
    "triggers": [
      {
        "git": {
          "pullRequest": {
            "action": "GIT_PULL_REQUEST_ACTION_OPENED",
            "repos": ["agentic-pantheon/aurey-mcp"],
            "ignoreDraftPrs": true
          }
        }
      }
    ],
    "actions": [{ "prComment": {} }],
    "prompts": [
      {
        "prompt": "Review the pull request diff on agentic-pantheon/aurey-mcp for security and wallet safety.\n\nScan for:\n- Leaked secrets: `1ck_`, `ocv_`, Alchemy API keys, private keys, or credentials committed to repo files\n- Secrets placed in MCP host JSON or env blocks where README expects ~/.aurey/mcp.env + run-aurey-wallet-mcp.sh wrapper instead\n- Regressions to the prepare → confirm → tx_execute(prepared_id=…) flow (tx_execute must only accept server-issued prepared_id)\n- Changes that bypass or weaken the ~/.aurey/mcp.env pattern documented in README\n\nPost one PR comment with findings: severity, file paths, and recommended fixes. If nothing concerning, say so briefly. Do not use GitHub APIs to block merge—use comment text only (e.g. clearly mark blocking issues in the comment). Do not merge."
      }
    ],
    "model": "",
    "agentOptions": { "skipInstall": false },
    "memoryEnabled": false
  }
}
```

---

## 3. PR install & docs drift — aurey-mcp

**Trigger:** Pull request opened and pushed (same repo)  
**Tools:** Comment on PRs; open/update PRs only if the agent must push doc regen (prefer comment-only)

```json
{
  "name": "PR install & docs drift — aurey-mcp",
  "description": "When install or website doc paths change, verify tests, build output, and install.sh sync.",
  "workflow": {
    "triggers": [
      {
        "git": {
          "pullRequest": {
            "action": "GIT_PULL_REQUEST_ACTION_OPENED",
            "repos": ["agentic-pantheon/aurey-mcp"],
            "ignoreDraftPrs": true
          }
        }
      },
      {
        "git": {
          "pullRequest": {
            "action": "GIT_PULL_REQUEST_ACTION_PUSHED",
            "repos": ["agentic-pantheon/aurey-mcp"],
            "ignoreDraftPrs": true
          }
        }
      }
    ],
    "actions": [{ "prComment": {} }, { "gitPr": {} }],
    "prompts": [
      {
        "prompt": "On pull request opened/pushed for agentic-pantheon/aurey-mcp, inspect the diff. Only run the full checklist when the PR touches any of: install/**, src/aurey_wallet_mcp/install_common.py, mcp_hosts*, setup*, scripts/build_website_docs.py, or host install markdown under install/.\n\nIf those paths are untouched, post a brief PR comment that install/docs drift checks were skipped.\n\nIf touched:\n1. Confirm test_mcp_hosts / install-related tests still apply; run relevant pytest targets (e.g. tests touching install or mcp hosts).\n2. Run `uv sync --group dev` then `uv run python scripts/build_website_docs.py` and report whether website output would change (generated HTML is not committed per docs/releasing.md—say what would differ).\n3. Compare install/install.sh with website/install.sh sync expectations (Pages workflow copies install.sh into website/).\n\nPost an actionable PR comment listing gaps. Prefer comment-only; only open or update a PR branch via git if the repo workflow explicitly allows bot pushes and the user flow permits doc regen commits—never commit secrets. Do not merge."
      }
    ],
    "model": "",
    "agentOptions": { "skipInstall": false },
    "memoryEnabled": false
  }
}
```

---

## 4. Release checklist — aurey-mcp

**Trigger:** Every Monday at 9:00 (cron `0 9 * * 1`)  
**Tools:** Open/update PRs (optional—for maintainer guidance only)  
**Git checkout:** `agentic-pantheon/aurey-mcp` @ `main`

```json
{
  "name": "Release checklist — aurey-mcp",
  "description": "Weekly maintainer reminder: walk docs/releasing.md and report pre-tag steps.",
  "workflow": {
    "triggers": [{ "cron": { "cron": "0 9 * * 1" } }],
    "actions": [{ "gitPr": {} }],
    "prompts": [
      {
        "prompt": "Scheduled release checklist for agentic-pantheon/aurey-mcp on main. Check out main and read docs/releasing.md end to end.\n\nRun locally in the agent environment:\n- `uv sync --group dev`\n- `uv run pytest`\n- `uv run ruff check .`\n\nCompare pyproject.toml version to latest git tag (if any). Note whether bundled LiFi tokens may need refresh (scripts/sync_bundled_lifi_tokens.py per releasing doc).\n\nProduce a concise maintainer report: what is done, what remains before tagging (version bump, changelog, LiFi sync, install doc preview commands), and verification steps after tag push. If an open release-oriented PR exists, you may comment on it with the checklist—do not auto-tag, auto-merge, or publish. Opening a GitHub issue/PR is optional only when a version bump is clearly needed and maintainers want a tracking PR; keep minimal."
      }
    ],
    "model": "",
    "gitConfig": { "repo": "agentic-pantheon/aurey-mcp", "branch": "main" },
    "agentOptions": { "skipInstall": false },
    "memoryEnabled": true
  }
}
```

---

## 5. Weekly LiFi token sync — aurey-mcp

**Trigger:** Every Monday at 6:00 (cron `0 6 * * 1`)  
**Tools:** Open/update PRs  
**Git checkout:** `agentic-pantheon/aurey-mcp` @ `main`

```json
{
  "name": "Weekly LiFi token sync — aurey-mcp",
  "description": "Refresh bundled LiFi tokens and open a PR when data changes.",
  "workflow": {
    "triggers": [{ "cron": { "cron": "0 6 * * 1" } }],
    "actions": [{ "gitPr": {} }],
    "prompts": [
      {
        "prompt": "On schedule, work on agentic-pantheon/aurey-mcp branch main per docs/releasing.md.\n\n1. `uv sync --group dev`\n2. Run `uv run python scripts/sync_bundled_lifi_tokens.py` with `--fetch` when network fetch is appropriate (otherwise use documented --from-file flow if maintainers pinned a source).\n3. Run `uv run pytest tests/test_bundled_lifi_tokens.py`\n\nIf bundled token data changed and tests pass, open a PR with a minimal commit message (e.g. \"chore: sync bundled LiFi tokens\"). If no data change, stop without opening a PR. Do not tag or release."
      }
    ],
    "model": "",
    "gitConfig": { "repo": "agentic-pantheon/aurey-mcp", "branch": "main" },
    "agentOptions": { "skipInstall": false },
    "memoryEnabled": false
  }
}
```

---

## Finish in editor

- Confirm GitHub integration and repo scope on each PR trigger.
- Enable **Cloud** compute if local pytest/ruff should run on PR branches.
- Save each automation after the prefilled form loads.
