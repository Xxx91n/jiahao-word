"""按 GLOSSARY.md 和 spec 的规则检查组文件，一次把所有问题列全。"""

from __future__ import annotations

import re
from collections.abc import Hashable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LANGUAGES = ("zh", "en")
PLAIN = "plain"
JARGON = "jargon"
SECTION_NAMES = {PLAIN: "大白话", JARGON: "黑话"}
GROUP_ID = re.compile(r"g[0-9]{4,}")


class _StrictLoader(yaml.SafeLoader):
    """同一个键写两次就报错，不让后一个悄悄盖掉前一个。"""


def _construct_unique_mapping(
    loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            # 合并进来的那份也可能自己写重了，先让它走一遍构造。
            loader.construct_object(value_node, deep=deep)
            continue
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            continue
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"键「{key}」重复了", key_node.start_mark
            )
        seen.add(key)
    return yaml.constructor.SafeConstructor.construct_mapping(loader, node, deep=deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class Problem:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}：{self.message}"


@dataclass
class Word:
    lang: str
    word: str
    env: str | None


@dataclass
class Group:
    where: str
    id: str
    label: str
    has_jargon: bool
    plain: list[Word]
    jargon: list[Word]


def normalize_word(lang: str, word: str) -> str:
    """查重用的写法：去掉首尾空格，英文不分大小写。"""
    text = word.strip()
    if lang == "en":
        return text.casefold()
    return text


def _word_key(word: Word) -> tuple[str, str]:
    return (word.lang, normalize_word(word.lang, word.word))


def _issue_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip().lstrip("#").strip()
        # "²" 也算数字字符，可 int() 会炸，所以只认 ASCII 数字。
        if text.isascii() and text.isdigit():
            try:
                number = int(text)
            except ValueError:
                return None
            return number if number > 0 else None
    return None


def _read_words(
    data: dict[str, Any],
    where: str,
    section: str,
    problems: list[Problem],
) -> tuple[list[Word], bool]:
    raw = data.get(section)
    if raw is None:
        return [], False
    if not isinstance(raw, list):
        problems.append(Problem(where, f"「{section}」应该是一串条目，现在不是"))
        return [], True

    words: list[Word] = []
    for number, item in enumerate(raw, start=1):
        spot = f"{where} 的{SECTION_NAMES[section]}第 {number} 条"
        if not isinstance(item, dict):
            problems.append(Problem(spot, "这一条不是键值对"))
            continue

        lang_value = item.get("lang")
        word_value = item.get("word")
        env_value = item.get("env")
        issue = item.get("issue")

        if not isinstance(lang_value, str) or not lang_value.strip():
            problems.append(Problem(spot, "缺语言标签，只能写 zh 或 en"))
            lang = None
        elif lang_value.strip() not in LANGUAGES:
            problems.append(
                Problem(
                    spot,
                    f"语言标签「{lang_value.strip()}」不合法，只能写 zh 或 en",
                )
            )
            lang = None
        else:
            lang = lang_value.strip()

        if not isinstance(word_value, str) or not word_value.strip():
            problems.append(Problem(spot, "缺词"))
            word = None
        else:
            word = word_value.strip()

        if issue is None:
            problems.append(Problem(spot, "缺 issue 编号"))
        elif _issue_number(issue) is None:
            problems.append(
                Problem(spot, f"issue 编号「{issue}」不对，得是正整数")
            )

        env = None
        if env_value is not None:
            if isinstance(env_value, str) and env_value.strip():
                env = env_value.strip()
            else:
                problems.append(
                    Problem(spot, "env 得是一句非空的话，用不上就别填")
                )

        if lang is not None and word is not None:
            words.append(Word(lang=lang, word=word, env=env))

    return words, len(raw) > 0


def _describe_yaml_error(error: Exception) -> str:
    detail = getattr(error, "problem", None)
    mark = getattr(error, "problem_mark", None)
    parts = []
    if mark is not None:
        parts.append(f"第 {mark.line + 1} 行")
    if detail:
        parts.append(str(detail))
    return "，".join(parts)


def _load_group(path: Path, problems: list[Problem]) -> Group | None:
    where = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        problems.append(Problem(where, f"这个文件读不了：{error}"))
        return None

    try:
        data = yaml.load(text, Loader=_StrictLoader)
    except Exception as error:
        # 写坏的 !!int / !!bool 会抛普通 Python 错误，不能让它带 traceback 退出。
        detail = _describe_yaml_error(error)
        message = "这个文件不是能读的 YAML"
        if detail:
            message = f"{message}：{detail}"
        problems.append(Problem(where, message))
        return None

    if not isinstance(data, dict):
        problems.append(Problem(where, "最外层应该是键值对，现在不是"))
        return None

    group_id = path.stem
    digits = group_id[1:]
    if (
        GROUP_ID.fullmatch(group_id) is None
        or int(digits) < 1
        or (len(digits) > 4 and digits.startswith("0"))
    ):
        problems.append(
            Problem(where, f"文件名「{path.name}」不是编号，编号得写成 g0001 这种")
        )

    raw_id = data.get("id")
    if raw_id is not None:
        text_id = raw_id.strip() if isinstance(raw_id, str) else raw_id
        if text_id != group_id:
            problems.append(
                Problem(
                    where,
                    f"文件名叫「{group_id}」，里面的编号写成了「{text_id}」，"
                    "两边得一样",
                )
            )

    raw_label = data.get("label")
    label = raw_label.strip() if isinstance(raw_label, str) else ""

    plain, _ = _read_words(data, where, PLAIN, problems)
    jargon, has_jargon = _read_words(data, where, JARGON, problems)

    return Group(
        where=where,
        id=group_id,
        label=label,
        has_jargon=has_jargon,
        plain=plain,
        jargon=jargon,
    )


def _group_files(groups_dir: Path) -> list[Path]:
    if not groups_dir.is_dir():
        return []
    files = [
        path
        for path in groups_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    ]
    return sorted(files, key=lambda path: path.name)


def _check_one_group(group: Group, problems: list[Problem]) -> None:
    if not group.has_jargon:
        problems.append(Problem(group.where, "这个组没有黑话，组得由一条黑话带出来"))

    plain_languages = {word.lang for word in group.plain}
    for word in group.jargon:
        if word.lang not in plain_languages:
            problems.append(
                Problem(
                    group.where,
                    f"黑话「{word.word}」写的是 {word.lang}，"
                    f"但这一组没有 {word.lang} 的大白话",
                )
            )

    seen: dict[tuple[str, str], list[Word]] = {}
    for word in group.plain:
        seen.setdefault(_word_key(word), []).append(word)
    for (lang, _), words in sorted(seen.items()):
        if len(words) > 1:
            problems.append(
                Problem(
                    group.where,
                    f"同一组里 {lang} 的大白话「{words[0].word}」重复了，"
                    f"写了 {len(words)} 次，只留一条",
                )
            )


def scan_groups(groups_dir: Path) -> tuple[list[Group], list[Problem], int]:
    """返回（读出来的组、所有问题、组文件个数）。有问题也不提前退出。"""
    problems: list[Problem] = []
    files = _group_files(groups_dir)
    if not files:
        if not groups_dir.is_dir():
            return [], [Problem(str(groups_dir), "找不到这个目录")], 0
        return [], [], 0

    groups: list[Group] = []
    for path in files:
        group = _load_group(path, problems)
        if group is not None:
            groups.append(group)

    stem_files: dict[str, list[str]] = {}
    for path in files:
        stem_files.setdefault(path.stem, []).append(str(path))
    for group_id, paths in sorted(stem_files.items()):
        if len(paths) > 1:
            problems.append(
                Problem(
                    paths[0],
                    f"编号「{group_id}」和 {'、'.join(paths[1:])} 重复了",
                )
            )

    for group in groups:
        _check_one_group(group, problems)

    word_groups: dict[tuple[str, str], set[str]] = {}
    for group in groups:
        for word in (*group.plain, *group.jargon):
            word_groups.setdefault(_word_key(word), set()).add(group.id)
    for group in groups:
        for word in (*group.plain, *group.jargon):
            if len(word_groups[_word_key(word)]) > 1 and word.env is None:
                problems.append(
                    Problem(
                        group.where,
                        f"「{word.word}」这个 {word.lang} 词在好几个组里都有，"
                        "这一条得填 env 说明用在什么场合",
                    )
                )

    return groups, problems, len(files)


def check_groups(groups_dir: Path) -> tuple[list[Problem], int]:
    """返回（所有问题，组文件个数）。"""
    _, problems, file_count = scan_groups(groups_dir)
    return problems, file_count
