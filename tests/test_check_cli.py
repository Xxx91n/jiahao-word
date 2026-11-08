"""只从命令行入口验证 check 的行为：跑子进程，看退出码和输出。"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GOOD_GROUP = """\
id: g0001
label: 把话说清楚
plain:
  - lang: zh
    word: 说清楚
    issue: 12
  - lang: en
    word: say it plainly
    issue: 12
jargon:
  - lang: zh
    word: 赋能
    issue: 12
  - lang: en
    word: leverage
    issue: 12
"""


def run_cli(groups: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "jiahao_word", "check", "--groups", str(groups)],
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


def run_check(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    groups = tmp_path / "groups"
    groups.mkdir()
    for name, content in files.items():
        (groups / name).write_text(
            textwrap.dedent(content).lstrip("\n"), encoding="utf-8"
        )
    return run_cli(groups)


def test_good_data_exits_zero(tmp_path: Path) -> None:
    result = run_check(tmp_path, {"g0001.yaml": GOOD_GROUP})

    assert result.returncode == 0
    assert "检查通过" in result.stdout
    assert result.stderr == ""


def test_duplicate_id_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": GOOD_GROUP,
            "g0001.yml": GOOD_GROUP,
        },
    )

    assert result.returncode == 1
    assert "重复" in result.stderr


def test_id_must_match_filename(tmp_path: Path) -> None:
    result = run_check(tmp_path, {"g0002.yaml": GOOD_GROUP})

    assert result.returncode == 1
    assert "两边得一样" in result.stderr


def test_filename_must_be_a_group_id(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {"notes.yaml": GOOD_GROUP.replace("id: g0001", "id: notes")},
    )

    assert result.returncode == 1
    assert "不是编号" in result.stderr


def test_zero_id_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {"g0000.yaml": GOOD_GROUP.replace("id: g0001", "id: g0000")},
    )

    assert result.returncode == 1
    assert "不是编号" in result.stderr


def test_group_without_jargon_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 只有大白话
                plain:
                  - lang: zh
                    word: 一句大白话
                    issue: 12
                jargon: []
                """
        },
    )

    assert result.returncode == 1
    assert "没有黑话" in result.stderr


def test_jargon_without_same_language_plain_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 少了英文大白话
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: 12
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                  - lang: en
                    word: leverage
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "没有 en 的大白话" in result.stderr


def test_invalid_language_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 语言标签写错了
                plain:
                  - lang: fr
                    word: bonjour
                    issue: 12
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "语言标签「fr」不合法" in result.stderr


def test_missing_issue_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 忘了写 issue
                plain:
                  - lang: zh
                    word: 说清楚
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "缺 issue 编号" in result.stderr


def test_same_word_in_two_groups_needs_env(tmp_path: Path) -> None:
    first = """\
        id: g0001
        label: 第一个组
        plain:
          - lang: zh
            word: 差不多的话
            issue: 12
        jargon:
          - lang: zh
            word: 黑话一
            issue: 12
        """
    second = """\
        id: g0002
        label: 第二个组
        plain:
          - lang: zh
            word: 差不多的话
            issue: 12
        jargon:
          - lang: zh
            word: 黑话二
            issue: 12
        """
    result = run_check(tmp_path, {"g0001.yaml": first, "g0002.yaml": second})

    assert result.returncode == 1
    assert "填 env" in result.stderr


def test_same_word_in_two_groups_with_env_passes(tmp_path: Path) -> None:
    first = """\
        id: g0001
        label: 第一个组
        plain:
          - lang: zh
            word: 差不多的话
            issue: 12
            env: 写给人看的场合
        jargon:
          - lang: zh
            word: 黑话一
            issue: 12
        """
    second = """\
        id: g0002
        label: 第二个组
        plain:
          - lang: zh
            word: 差不多的话
            issue: 12
            env: 写给机器看的场合
        jargon:
          - lang: zh
            word: 黑话二
            issue: 12
        """
    result = run_check(tmp_path, {"g0001.yaml": first, "g0002.yaml": second})

    assert result.returncode == 0
    assert "检查通过" in result.stdout


def test_duplicate_plain_ignores_spaces_and_english_case(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 同组重复
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: 12
                  - lang: zh
                    word: "  说清楚  "
                    issue: 12
                  - lang: en
                    word: Say It Plainly
                    issue: 12
                  - lang: en
                    word: " say it plainly "
                    issue: 12
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "重复" in result.stderr


def test_all_problems_are_listed_at_once(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 一堆问题
                plain:
                  - lang: fr
                    word: bonjour
                    issue: 12
                  - lang: zh
                    word: 没写编号的大白话
                  - lang: zh
                    word: 没写编号的大白话
                jargon: []
                """
        },
    )

    assert result.returncode == 1
    assert "语言标签「fr」不合法" in result.stderr
    assert "缺 issue 编号" in result.stderr
    assert "没有黑话" in result.stderr
    assert "重复" in result.stderr


def test_non_ascii_issue_number_is_caught_without_crashing(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 编号写法不对
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: "²"
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "issue 编号「²」不对" in result.stderr
    assert "Traceback" not in result.stderr


def test_duplicate_yaml_key_is_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 键重复了
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: 12
                plain:
                  - lang: en
                    word: say it plainly
                    issue: 12
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "键「plain」重复了" in result.stderr


def test_yaml_merge_keys_still_pass(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                defaults: &defaults
                  lang: zh
                  issue: 12
                plain:
                  - <<: *defaults
                    word: 说清楚
                jargon:
                  - <<: *defaults
                    word: 赋能
                """
        },
    )

    assert result.returncode == 0
    assert "检查通过" in result.stdout


def test_unhashable_yaml_key_does_not_crash(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                ? [a, b]
                : 1
                """
        },
    )

    assert result.returncode == 1
    assert "不是能读的 YAML" in result.stderr
    assert "Traceback" not in result.stderr


def test_broken_explicit_tag_does_not_crash(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 标签写坏了
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: !!int "abc"
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "不是能读的 YAML" in result.stderr
    assert "Traceback" not in result.stderr


def test_duplicate_keys_inside_merge_source_are_caught(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 合并来源里重复
                plain:
                  - <<: {lang: zh, lang: en}
                    word: 说清楚
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "键「lang」重复了" in result.stderr
    assert "Traceback" not in result.stderr


def test_errors_from_two_files_are_listed_together(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": """\
                id: g0001
                label: 只有大白话
                plain:
                  - lang: zh
                    word: 一句大白话
                    issue: 12
                jargon: []
                """,
            "g0002.yaml": """\
                id: g0002
                label: 语言写错了
                plain:
                  - lang: fr
                    word: bonjour
                    issue: 12
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """,
        },
    )

    assert result.returncode == 1
    assert "没有黑话" in result.stderr
    assert "语言标签「fr」不合法" in result.stderr


def test_huge_issue_number_does_not_crash(tmp_path: Path) -> None:
    result = run_check(
        tmp_path,
        {
            "g0001.yaml": f"""\
                id: g0001
                label: 编号太长
                plain:
                  - lang: zh
                    word: 说清楚
                    issue: "{'1' * 5000}"
                jargon:
                  - lang: zh
                    word: 赋能
                    issue: 12
                """
        },
    )

    assert result.returncode == 1
    assert "issue 编号" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_groups_directory_exits_one(tmp_path: Path) -> None:
    result = run_cli(tmp_path / "nope")

    assert result.returncode == 1
    assert "找不到这个目录" in result.stderr
