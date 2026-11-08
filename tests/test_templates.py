"""只从命令行入口验证新模板：填好人话说明的 PR 描述能过 check-pr。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PR_TEMPLATE = REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
HUMAN_NOTE = (
    "我在让它解释报错日志时看到「优雅降级」；"
    "我改成「出错时少用几项功能，别整个挂掉」，同事一看就懂。"
)


def run_check_pr_on_body(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "jiahao_word", "check-pr"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=body,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONIOENCODING": "utf-8",
        },
    )


def fill_human_note(template: str, text: str) -> str:
    """照模板填：在人话说明标题下加一句人写的正文，其余原样保留。"""
    lines = template.splitlines()
    heading = next(
        index for index, line in enumerate(lines) if line.strip() == "## 人话说明"
    )
    return "\n".join([*lines[: heading + 1], "", text, *lines[heading + 1 :]]) + "\n"


def test_filled_pull_request_template_passes_check_pr() -> None:
    template = PR_TEMPLATE.read_text(encoding="utf-8")
    result = run_check_pr_on_body(fill_human_note(template, HUMAN_NOTE))

    assert result.returncode == 0
    assert "检查通过" in result.stdout
    assert result.stderr == ""


def test_unfilled_pull_request_template_is_blocked() -> None:
    template = PR_TEMPLATE.read_text(encoding="utf-8")
    result = run_check_pr_on_body(template)

    assert result.returncode == 1
    assert "是空的" in result.stderr
