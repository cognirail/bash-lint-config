"""命令入口：``cognirail-bash-lint-config check|fix [路径...]``。

顺序：内联逃逸守卫 → shellcheck → shfmt。任一失败返回 1。
Bash 文件 = ``*.sh`` / ``*.bash``，或无后缀但 shebang 为 bash/sh 的文件。
文件枚举尊重 git 忽略规则（不在 git 仓内时按目录遍历并跳过依赖/派生目录）。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cognirail_bash_lint_config import __version__, shellcheck_args, shfmt_args

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "dist", "build", "__pycache__"})
SHELL_SUFFIXES = frozenset({".sh", ".bash"})
SHEBANG = re.compile(rb"^#!\s*(?:/usr/bin/env\s+)?(?:bash|sh)\b")
# 源码内联逃逸：例外只能写进项目文档并由 review 决定，不在脚本里关规则。
ESCAPE_HATCH = re.compile(
    r"^\s*#\s*shellcheck\s+(?:disable|enable|shell|source-path|external-sources)\b"
)


@dataclass(frozen=True)
class Result:
    """单个步骤的结果。"""

    step: str
    ok: bool
    detail: str = ""


def _run(cmd: Sequence[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _git_files(root: Path) -> list[Path] | None:
    code, out = _run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], root)
    if code != 0:
        return None
    return [root / p for p in out.split("\0") if p]


def _walk(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            yield Path(dirpath) / name


def is_shell(path: Path) -> bool:
    """按后缀或 shebang 判定是否 Bash 脚本。"""
    if path.suffix in SHELL_SUFFIXES:
        return True
    if path.suffix:
        return False
    try:
        with path.open("rb") as handle:
            return bool(SHEBANG.match(handle.read(64)))
    except OSError:
        return False


def discover(root: Path, targets: Sequence[Path]) -> list[Path]:
    """找出要检查的 Bash 文件；``targets`` 为空表示整个项目。"""
    files = _git_files(root)
    candidates = files if files is not None else list(_walk(root))
    wanted = [t.resolve() for t in targets] or [root]
    return sorted(
        path
        for path in candidates
        if path.is_file()
        and not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
        and any(path == w or w in path.parents for w in wanted)
        and is_shell(path)
    )


def find_escape_hatches(files: Iterable[Path], root: Path) -> list[str]:
    """返回所有 ``# shellcheck disable=`` 等内联指令的位置。"""
    found: list[str] = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        found.extend(
            f"{path.relative_to(root)}:{index}: {line.strip()[:120]}"
            for index, line in enumerate(lines, start=1)
            if ESCAPE_HATCH.match(line)
        )
    return found


def run_shellcheck(root: Path, files: Sequence[Path]) -> Result:
    """shellcheck，基线全部启用。"""
    code, out = _run(["shellcheck", *shellcheck_args(), *map(str, files)], root)
    return Result("shellcheck", ok=code == 0, detail=out)


def run_shfmt(root: Path, files: Sequence[Path], *, fix: bool) -> Result:
    """shfmt：check 显示 diff，fix 原地改写。"""
    mode = "-w" if fix else "-d"
    code, out = _run(["shfmt", *shfmt_args(), mode, *map(str, files)], root)
    return Result("shfmt", ok=code == 0, detail=out)


def report(results: Iterable[Result]) -> int:
    """打印每步结果，返回进程退出码。"""
    failed = False
    for result in results:
        print(f"[{'ok  ' if result.ok else 'FAIL'}] {result.step}")
        if not result.ok and result.detail:
            print(result.detail)
            failed = True
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    """解析参数并执行。"""
    parser = argparse.ArgumentParser(prog="cognirail-bash-lint-config")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "command", choices=("check", "fix"), help="check 只报告；fix 用 shfmt 原地格式化"
    )
    parser.add_argument("paths", nargs="*", type=Path, help="限定检查的文件或目录，默认整个项目")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="项目根目录，默认当前目录")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    files = discover(root, args.paths)
    if not files:
        print("没有发现 Bash 文件。")
        return 0
    print(f"Bash {len(files)} 个文件（{root}）")

    hatches = find_escape_hatches(files, root)
    guard = Result(
        "escape-hatch",
        ok=not hatches,
        detail="脚本内的 shellcheck 指令不允许，规则例外请在 review 中决定：\n"
        + "\n".join(hatches),
    )
    results = [
        guard,
        run_shellcheck(root, files),
        run_shfmt(root, files, fix=args.command == "fix"),
    ]
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
