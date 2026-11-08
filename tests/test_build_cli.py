"""只从命令行入口验证 build：跑子进程，看改了什么、生成了什么。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

GROUP_ONE = """\
id: g0001
label: 把话说清楚
plain:
  - lang: zh
    word: 说清楚
    issue: 12
  - lang: en
    word: Say It Plainly
    issue: 12
jargon:
  - lang: zh
    word: 赋能
    issue: 12
  - lang: en
    word: leverage
    issue: 12
"""

GROUP_TWO = """\
id: g0002
label: 别绕弯子
plain:
  - lang: zh
    word: 直接说
    issue: 13
jargon:
  - lang: zh
    word: 抓手
    issue: 13
"""

README_PREFIX = "# 标题\n\n手写的介绍不能动。\n\n"
README_SUFFIX = "\n\n页脚也不动。\n"
README = (
    README_PREFIX
    + "<!-- generated:start -->\n旧内容\n<!-- generated:end -->"
    + README_SUFFIX
)


def run_build(
    groups: Path, readme: Path, index_dir: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "jiahao_word",
            "build",
            "--groups",
            str(groups),
            "--readme",
            str(readme),
            "--index-dir",
            str(index_dir),
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


def make_data(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path, Path]:
    groups = tmp_path / "groups"
    groups.mkdir(parents=True)
    for name, content in files.items():
        (groups / name).write_text(
            textwrap.dedent(content).lstrip("\n"), encoding="utf-8"
        )
    readme = tmp_path / "README.md"
    readme.write_text(README, encoding="utf-8")
    index_dir = tmp_path / "index"
    return groups, readme, index_dir


def test_only_the_generated_block_is_replaced(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(tmp_path, {"g0001.yaml": GROUP_ONE})

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 0
    text = readme.read_text(encoding="utf-8")
    assert text.startswith(README_PREFIX)
    assert text.endswith(README_SUFFIX)
    assert "旧内容" not in text
    assert "| 赋能 (zh) | 说清楚 (zh)、Say It Plainly (en) | 把话说清楚 | — |" in text
    assert "| leverage (en) | Say It Plainly (en)、说清楚 (zh) | 把话说清楚 | — |" in text


def test_index_is_generated_per_language(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(tmp_path, {"g0001.yaml": GROUP_ONE})

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 0
    zh = json.loads((index_dir / "zh.json").read_text(encoding="utf-8"))
    en = json.loads((index_dir / "en.json").read_text(encoding="utf-8"))

    assert zh["赋能"] == [
        {"env": None, "group": "g0001", "kind": "jargon", "label": "把话说清楚"}
    ]
    assert zh["说清楚"][0]["kind"] == "plain"
    assert en["leverage"][0]["kind"] == "jargon"
    assert en["say it plainly"][0]["kind"] == "plain"
    assert en["say it plainly"][0]["group"] == "g0001"


def test_running_twice_produces_the_same_files(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(
        tmp_path,
        {
            "g0002.yaml": GROUP_TWO,
            "g0001.yaml": GROUP_ONE,
        },
    )

    first = run_build(groups, readme, index_dir)
    assert first.returncode == 0

    readme_before = readme.read_bytes()
    zh_before = (index_dir / "zh.json").read_bytes()
    en_before = (index_dir / "en.json").read_bytes()

    second = run_build(groups, readme, index_dir)
    assert second.returncode == 0

    assert readme.read_bytes() == readme_before
    assert (index_dir / "zh.json").read_bytes() == zh_before
    assert (index_dir / "en.json").read_bytes() == en_before


def test_groups_are_rendered_in_id_order(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(
        tmp_path,
        {
            "g0002.yaml": GROUP_TWO,
            "g0001.yaml": GROUP_ONE,
        },
    )

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 0
    text = readme.read_text(encoding="utf-8")
    assert text.index("赋能") < text.index("抓手")


def test_group_order_is_numeric_not_lexicographic(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(
        tmp_path,
        {
            "g10000.yaml": """\
                id: g10000
                label: 一万
                plain:
                  - lang: zh
                    word: 白话乙
                    issue: 12
                jargon:
                  - lang: zh
                    word: 黑话乙
                    issue: 12
                """,
            "g9999.yaml": """\
                id: g9999
                label: 九千
                plain:
                  - lang: zh
                    word: 白话甲
                    issue: 12
                jargon:
                  - lang: zh
                    word: 黑话甲
                    issue: 12
                """,
        },
    )

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 0
    text = readme.read_text(encoding="utf-8")
    assert text.index("黑话甲") < text.index("黑话乙")


def test_two_fresh_runs_produce_the_same_files(tmp_path: Path) -> None:
    files = {"g0002.yaml": GROUP_TWO, "g0001.yaml": GROUP_ONE}
    first_groups, first_readme, first_index = make_data(tmp_path / "first", files)
    second_groups, second_readme, second_index = make_data(tmp_path / "second", files)

    first = run_build(first_groups, first_readme, first_index)
    second = run_build(second_groups, second_readme, second_index)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first_readme.read_bytes() == second_readme.read_bytes()
    assert (first_index / "zh.json").read_bytes() == (
        second_index / "zh.json"
    ).read_bytes()
    assert (first_index / "en.json").read_bytes() == (
        second_index / "en.json"
    ).read_bytes()


def test_missing_markers_exits_one_and_writes_nothing(tmp_path: Path) -> None:
    groups, _readme, index_dir = make_data(tmp_path, {"g0001.yaml": GROUP_ONE})
    readme = tmp_path / "README.md"
    readme.write_text("# 没有标记\n", encoding="utf-8")

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 1
    assert "generated:start" in result.stderr
    assert readme.read_text(encoding="utf-8") == "# 没有标记\n"
    assert not index_dir.exists()


def test_bad_data_exits_one_and_writes_nothing(tmp_path: Path) -> None:
    groups, readme, index_dir = make_data(
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
    before = readme.read_bytes()

    result = run_build(groups, readme, index_dir)

    assert result.returncode == 1
    assert "数据有问题" in result.stderr
    assert "没有黑话" in result.stderr
    assert readme.read_bytes() == before
    assert not index_dir.exists()
