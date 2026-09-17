# cognirail-bash-lint-config

Opinionated **shellcheck + shfmt** baseline for Bash — the shell sister of
[`@cognirail/eslint-config`](https://github.com/cognirail/eslint-config) and
[`cognirail-python-lint-config`](https://github.com/cognirail/python-lint-config).

Designed as **AI coding guardrails**: shellcheck at `style` severity with every optional check on,
machine-decided formatting, and **no inline escape hatches**. One package, one command, zero config.

## What it runs

| Tool | Purpose | Baseline |
| ---- | ------- | -------- |
| [`shellcheck`](https://www.shellcheck.net/) | Static analysis — `--severity=style`, all 11 optional checks enabled | `configs/shellcheckrc` |
| [`shfmt`](https://github.com/mvdan/sh) | Formatting — 2-space indent, indented `case`, binary ops at line start, simplified | `configs/shfmt.txt` |
| escape-hatch guard | Rejects `# shellcheck disable=` / `enable=` / `shell=` / `source-path=` inside scripts | built in |

Both binaries ship inside the wheels (`shellcheck-py`, `shfmt-py`) and are **pinned exactly**, so no
Homebrew/apt step and every consumer lints with the same engine.

## Requirements

- **Python** >= 3.11 (only as the runner; your scripts stay Bash)
- **uv** (recommended) or any PEP 517 installer

## Quick start

### 1. Install

```bash
uv add --dev cognirail-bash-lint-config
# or, for a local checkout:
uv add --dev --editable /path/to/bash-lint-config
```

### 2. Run

```bash
uv run cognirail-bash-lint-config check   # shellcheck + shfmt -d
uv run cognirail-bash-lint-config fix     # shfmt -w, then shellcheck
uv run cognirail-bash-lint-config check tools/ deploy/   # limit to paths
```

Bash files are `*.sh`, `*.bash`, or extension-less files whose shebang is `bash`/`sh`. Discovery uses
`git ls-files` (respecting `.gitignore`); outside a git repo the tree is walked and `.venv/`,
`node_modules/`, `dist/`, `build/` are skipped.

### 3. Project-level configuration

There is none. shellcheck does not accept an external rc path, so the baseline is translated into
command-line flags by the CLI and cannot be overridden by a project `.shellcheckrc`. If a rule is
genuinely wrong for a script, the fix is a code change or a reviewed exception documented next to the
script — never a directive inside it.

## Rule philosophy

- **Severity `style`.** Everything shellcheck knows about is reported, including stylistic findings
  (`SC2250` braces, `SC2292` `[[ ]]`, `SC2312` masked returns …).
- **All optional checks on.** `add-default-case`, `avoid-negated-conditions`, `avoid-nullary-conditions`,
  `check-extra-masked-returns`, `check-set-e-suppressed`, `check-unassigned-uppercase`, `deprecate-which`,
  `quote-safe-variables`, `require-double-brackets`, `require-variable-braces`, `useless-use-of-cat`.
- **Formatting is not a discussion.** `shfmt -ln bash -i 2 -ci -bn -sr -s`.
- **No inline escape hatches.** `# shellcheck disable=…` and friends fail the run — the same stance as
  eslint-config's `no-inline-eslint-config` and `noInlineConfig: true`.

## Development

```bash
uv sync
uv run scripts/smoke.py                       # temp-project smoke test (mirrors eslint-config/scripts/smoke.mjs)
uvx cognirail-python-lint-config check        # this package's Python follows the sister baseline via its public CLI
uv run cognirail-bash-lint-config check      # (no Bash in this repo; sanity: exits 0)

The sister baseline is consumed only through its CLI (it syncs `.cognirail/ruff-baseline.toml`); the two
repositories have no path dependency on each other.
```

## Versioning

- Patch: docs, comment wording.
- Minor: tool version bumps that do not add findings to a clean consumer.
- Major: new checks enabled or tool upgrades that can fail previously clean consumers.

## License

ISC
