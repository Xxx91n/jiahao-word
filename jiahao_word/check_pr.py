"""检查 PR 描述里的「人话说明」段有没有真内容。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .check import Problem

SECTION_NAME = "人话说明"

_ATX_HEADING = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_RULE = re.compile(r"^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)


@dataclass(frozen=True)
class _Heading:
    index: int
    level: int
    title: str


def _headings(lines: list[str]) -> list[_Heading]:
    """找标题所在的行下标；代码块里的井号不算。"""
    found: list[_Heading] = []
    fence: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        fence_match = _FENCE.match(line)
        if fence is not None:
            if (
                fence_match
                and fence_match.group(1)[0] == fence
                and len(fence_match.group(1)) >= fence_length
                and not fence_match.group(2).strip()
            ):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)[0]
            fence_length = len(fence_match.group(1))
            continue
        heading = _ATX_HEADING.match(line)
        if heading:
            found.append(
                _Heading(
                    index=index,
                    level=len(heading.group(1)),
                    title=heading.group(2).strip(),
                )
            )
    return found


def _has_content(section: str) -> bool:
    """只算看得见的大白话；注释、分隔线、小标题、围栏线都不算内容。"""
    text = _COMMENT.sub("", section)
    for line in text.splitlines():
        if not line.strip():
            continue
        if _ATX_HEADING.match(line) or _RULE.match(line) or _FENCE.match(line):
            continue
        if line.translate(_INVISIBLE).strip():
            return True
    return False


def check_pr_body(text: str) -> list[Problem]:
    """段不在、或段里只有空白，都算问题；有实际内容就没有问题。"""
    lines = text.splitlines()
    headings = _headings(lines)

    target: _Heading | None = None
    for heading in headings:
        if heading.level == 2 and heading.title == SECTION_NAME:
            target = heading
            break
    if target is None:
        return [Problem("PR 描述", f"缺「## {SECTION_NAME}」这一段，补上再跑一次")]

    end = len(lines)
    for heading in headings:
        if heading.index > target.index and heading.level <= 2:
            end = heading.index
            break

    section = "\n".join(lines[target.index + 1 : end])
    if _has_content(section):
        return []
    return [
        Problem("PR 描述", f"「## {SECTION_NAME}」这一段是空的，写点实际内容再跑一次")
    ]
