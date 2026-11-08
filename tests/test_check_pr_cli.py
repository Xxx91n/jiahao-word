"""只从命令行入口验证 check-pr：跑子进程，看退出码和输出。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_check_pr(body_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "jiahao_word",
            "check-pr",
            "--body-file",
            str(body_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONIOENCODING": "utf-8",
        },
    )


def run_body(tmp_path: Path, body: str) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "pr-body.md"
    path.write_text(body, encoding="utf-8")
    return run_check_pr(path)


def test_missing_section_exits_one(tmp_path: Path) -> None:
    result = run_body(tmp_path, "# 标题\n\n这里只有正文，没有那一段。\n")

    assert result.returncode == 1
    assert "缺「## 人话说明」" in result.stderr


def test_whitespace_only_section_exits_one(tmp_path: Path) -> None:
    result = run_body(tmp_path, "## 人话说明\n\n   \n\t\n")

    assert result.returncode == 1
    assert "是空的" in result.stderr


def test_section_with_real_text_exits_zero(tmp_path: Path) -> None:
    result = run_body(
        tmp_path,
        "## 人话说明\n\n这段说的是把机器话翻成人能懂的话。\n",
    )

    assert result.returncode == 0
    assert "检查通过" in result.stdout
    assert result.stderr == ""


def test_text_in_a_later_section_does_not_count(tmp_path: Path) -> None:
    result = run_body(
        tmp_path,
        "## 人话说明\n\n## 别的段\n\n这里才有字。\n",
    )

    assert result.returncode == 1
    assert "是空的" in result.stderr


def test_heading_inside_code_fence_is_not_a_section(tmp_path: Path) -> None:
    result = run_body(
        tmp_path,
        "```markdown\n## 人话说明\n\n这里才有字。\n```\n",
    )

    assert result.returncode == 1
    assert "缺「## 人话说明」" in result.stderr


def test_unreadable_body_file_exits_one(tmp_path: Path) -> None:
    result = run_check_pr(tmp_path / "missing.md")

    assert result.returncode == 1
    assert "读不了" in result.stderr
    assert "Traceback" not in result.stderr
