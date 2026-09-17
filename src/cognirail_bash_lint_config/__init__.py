"""cognirail-bash-lint-config —— Bash 的 shellcheck + shfmt 基线（AI coding guardrails）。

公开 API：

* :data:`SHELLCHECK_BASELINE` / :data:`SHFMT_BASELINE`：基线文件路径；
* :func:`shellcheck_args` / :func:`shfmt_args`：基线解析成的命令行参数。
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

__version__ = "0.1.0"

_CONFIGS = files(__package__) / "configs"
SHELLCHECK_BASELINE: Path = Path(str(_CONFIGS / "shellcheckrc"))
SHFMT_BASELINE: Path = Path(str(_CONFIGS / "shfmt.txt"))


def _lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def shellcheck_args() -> list[str]:
    """把 shellcheckrc 基线转成 ``--key=value`` 参数（shellcheck 不接受外部 rc 路径）。"""
    args: list[str] = []
    for line in _lines(SHELLCHECK_BASELINE):
        key, _, value = line.partition("=")
        if key == "external-sources":
            if value == "true":
                args.append("--external-sources")
            continue
        args.append(f"--{key}={value}")
    return args


def shfmt_args() -> list[str]:
    """把 shfmt 基线转成参数列表。"""
    return [part for line in _lines(SHFMT_BASELINE) for part in line.split()]


__all__ = ["SHELLCHECK_BASELINE", "SHFMT_BASELINE", "__version__", "shellcheck_args", "shfmt_args"]
