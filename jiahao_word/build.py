"""把组数据生成成 README 里的对照表和按语言的检索索引。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .check import JARGON, LANGUAGES, PLAIN, Group, normalize_word, scan_groups

START_MARKER = "<!-- generated:start -->"
END_MARKER = "<!-- generated:end -->"
TABLE_HEADER = (
    "| 黑话 | 大白话 | 标签 | 用在哪 |\n"
    "| --- | --- | --- | --- |"
)


class BuildError(Exception):
    """生成不了时抛这个，命令行只打印一句话，不带 traceback。"""


def _language_rank(lang: str) -> int:
    """zh 在前、en 在后，排序才稳定。"""
    return LANGUAGES.index(lang)


def _table_cell(text: str) -> str:
    """把内容收拾成能放进 Markdown 表格的一格。"""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def _format_word(word) -> str:
    """词后面带上语言标签。"""
    return f"{_table_cell(word.word)} ({word.lang})"


def _word_sort_key(word) -> tuple[int, str]:
    """先按语言顺序，再按查重时用的写法。"""
    return (_language_rank(word.lang), normalize_word(word.lang, word.word))


def _group_id_sort_key(group_id: str) -> tuple[int, str]:
    """按编号里的数字排，g9999 排在 g10000 前面。"""
    digits = group_id[1:]
    return (int(digits) if digits.isdigit() else 0, group_id)


def _group_sort_key(group: Group) -> tuple[int, str]:
    """组的排序键。"""
    return _group_id_sort_key(group.id)


def _plain_text(group: Group, jargon_lang: str) -> str:
    """同一种语言的大白话排前面，再排别的语言。"""
    words = sorted(
        group.plain,
        key=lambda word: (
            word.lang != jargon_lang,
            _language_rank(word.lang),
            normalize_word(word.lang, word.word),
        ),
    )
    return "、".join(_format_word(word) for word in words)


def render_table(groups: list[Group]) -> str:
    """一条黑话一行，大白话那一列把各组语言的说法全列出来。"""
    lines = [TABLE_HEADER]
    for group in sorted(groups, key=_group_sort_key):
        for word in sorted(group.jargon, key=_word_sort_key):
            plain = _plain_text(group, word.lang) or "—"
            env = _table_cell(word.env) if word.env else "—"
            label = _table_cell(group.label) if group.label else "—"
            lines.append(f"| {_format_word(word)} | {plain} | {label} | {env} |")
    return "\n".join(lines)


def render_indexes(groups: list[Group]) -> dict[str, str]:
    """每种语言一份 JSON：查一个词，拿到它所在的组。

    返回结果里的标签和 env 只用来区分候选，不拿它们查词。
    """
    buckets: dict[str, dict[str, list[dict[str, str | None]]]] = {
        lang: {} for lang in LANGUAGES
    }
    for group in sorted(groups, key=_group_sort_key):
        for kind, words in ((JARGON, group.jargon), (PLAIN, group.plain)):
            for word in words:
                key = normalize_word(word.lang, word.word)
                buckets[word.lang].setdefault(key, []).append(
                    {
                        "group": group.id,
                        "label": group.label,
                        "kind": kind,
                        "env": word.env,
                    }
                )

    result: dict[str, str] = {}
    for lang in LANGUAGES:
        entries = buckets[lang]
        for key, candidates in entries.items():
            candidates.sort(
                key=lambda item: (
                    _group_id_sort_key(item["group"] or ""),
                    item["kind"] or "",
                    item["env"] or "",
                )
            )
        result[lang] = (
            json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    return result


def _stage(path: Path, content: str) -> Path:
    """把内容写到同目录的临时文件，返回临时文件的路径。"""
    fd, name = tempfile.mkstemp(
        dir=path.parent, prefix=path.name + ".", suffix=".tmp"
    )
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content.encode("utf-8"))
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            mode = 0o644
        os.chmod(temp, mode)
    except OSError:
        temp.unlink(missing_ok=True)
        raise
    return temp


def replace_block(text: str, table: str) -> str:
    """只动两个标记之间的东西，标记外面的一个字符都不碰。"""
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise BuildError(
            f"README 里要正好有一个 {START_MARKER} 和一个 {END_MARKER}"
        )
    start = text.index(START_MARKER) + len(START_MARKER)
    end = text.index(END_MARKER)
    if end < start:
        raise BuildError("README 里生成标记的顺序反了")
    return text[:start] + "\n" + table + "\n" + text[end:]


def generate(groups_dir: Path, readme_path: Path, index_dir: Path) -> tuple[int, int]:
    """生成对照表和索引，返回（组数、索引份数）。数据有问题就不写文件。"""
    groups, problems, _ = scan_groups(groups_dir)
    if problems:
        raise BuildError(
            "数据有问题，先改好再生成：\n" + "\n".join(str(problem) for problem in problems)
        )

    try:
        text = readme_path.read_bytes().decode("utf-8")
    except OSError as error:
        raise BuildError(f"README 读不了：{error}") from error
    except UnicodeDecodeError as error:
        raise BuildError(f"README 不是 UTF-8 文本：{error}") from error

    table = render_table(groups)
    new_text = replace_block(text, table)
    indexes = render_indexes(groups)

    staged: list[tuple[Path, Path]] = []
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        for lang, content in indexes.items():
            target = index_dir / f"{lang}.json"
            staged.append((_stage(target, content), target))
        staged.append((_stage(readme_path, new_text), readme_path))
        # 内容先全写进临时文件，再逐个换上去；写临时文件失败时已有文件不动。
        # 多个文件之间不是一次原子操作，换到一半失败要靠漂移检查发现。
        for temp, target in staged:
            os.replace(temp, target)
    except OSError as error:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)
        raise BuildError(f"写文件失败：{error}") from error

    return len(groups), len(indexes)
