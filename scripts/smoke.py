"""冒烟测试：在临时项目上验证 shellcheck / shfmt 基线与守卫。用法：``uv run scripts/smoke.py``。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cognirail_bash_lint_config.cli import main

CLEAN = """#!/usr/bin/env bash
set -euo pipefail

main() {
  local name="${1:-world}"
  case "${name}" in
    world) echo "hello, ${name}" ;;
    *) echo "hi, ${name}" ;;
  esac
}

main "$@"
"""

# 未加引号、`which`、单中括号、缺 default case、缩进 4 空格。
DIRTY = """#!/bin/bash
    FOO=$1
if [ $FOO = a ]; then
  which ls
fi
case $FOO in
  a) echo a;;
esac
"""

# 内联逃逸拆开拼接，避免本文件自己触发守卫。
HATCH = "#!/usr/bin/env bash\n# shellcheck " + "disable=SC2086\necho $1\n"

NO_SUFFIX = "#!/usr/bin/env bash\necho ok\n"


def _project(tmp: Path, **files: str) -> Path:
    root = tmp / "proj"
    root.mkdir(parents=True)
    for name, body in files.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


def _check(root: Path, *args: str) -> int:
    return main([*args, "--root", str(root)])


class SmokeFailure(SystemExit):
    """某条断言不成立。"""

    def __init__(self, message: str) -> None:
        super().__init__(f"smoke 失败：{message}")


def expect(condition: object, message: str) -> None:
    """条件不成立时以明确信息终止。"""
    if not condition:
        raise SmokeFailure(message)


def run() -> None:
    """执行全部断言。"""
    with tempfile.TemporaryDirectory(prefix="cognirail-bash-lint-config-smoke-") as tmpdir:
        tmp = Path(tmpdir)

        clean = _project(tmp / "a", **{"clean.sh": CLEAN})
        expect(_check(clean, "check") == 0, "干净脚本应通过")

        dirty = _project(tmp / "b", **{"dirty.sh": DIRTY})
        expect(_check(dirty, "check") == 1, "未加引号 / which / 单中括号 / 缺 default case 应失败")
        expect(_check(dirty, "fix") == 1, "fix 只修格式，shellcheck 问题仍应失败")
        expect("    FOO" not in (dirty / "dirty.sh").read_text(encoding="utf-8"), "fix 应重排缩进")

        hatch = _project(tmp / "c", **{"hatch.sh": HATCH})
        expect(_check(hatch, "check") == 1, "脚本内 shellcheck disable 应被守卫拒绝")

        rc = _project(
            tmp / "e",
            **{"rc.sh": "#!/usr/bin/env bash\necho $1\n", ".shellcheckrc": "disable=SC2086\n"},
        )
        expect(_check(rc, "check") == 1, "项目 .shellcheckrc 不应能关掉基线规则")

        bare = _project(tmp / "d", **{"run": NO_SUFFIX, "notes.txt": "not a script\n"})
        expect(
            _check(bare, "check") == 0, "无后缀但带 bash shebang 的文件应被识别并通过；txt 不参与"
        )

    print("smoke ok")


if __name__ == "__main__":
    run()
