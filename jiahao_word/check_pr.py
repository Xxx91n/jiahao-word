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


@dataclass(frozen=True)
class _Fence:
    char: str
    length: int


def _fence_state(fence: _Fence | None, line: str) -> tuple[_Fence | None, str]:
    """看这一行对围栏做了什么：开、关、围栏里的正文，还是围栏外的普通行。"""
    match = _FENCE.match(line)
    if fence is None:
        if match:
            return _Fence(match.group(1)[0], len(match.group(1))), "open"
        return None, "text"
    if (
        match
        and match.group(1)[0] == fence.char
        and len(match.group(1)) >= fence.length
        and not match.group(2).strip()
    ):
        return None, "close"
    return fence, "inside"


def _headings(lines: list[str]) -> list[_Heading]:
    """找标题所在的行下标；代码块里的井号不算。"""
    found: list[_Heading] = []
    fence: _Fence | None = None
    for index, line in enumerate(lines):
        fence, state = _fence_state(fence, line)
        if state != "text":
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
    fence: _Fence | None = None
    for line in text.splitlines():
        fence, state = _fence_state(fence, line)
        if state in {"open", "close"}:
            continue
        if state == "text":
            if not line.strip():
                continue
            if _ATX_HEADING.match(line) or _RULE.match(line):
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
