"""检查 PR 描述里的「人话说明」段有没有真内容。"""

from __future__ import annotations

import re

from .check import Problem

SECTION_NAME = "人话说明"

_ATX_HEADING = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})(.*)$")


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """返回（行号，层级，标题）；代码块里的井号不算。"""
    found: list[tuple[int, int, str]] = []
    fence: str | None = None
    fence_length = 0
    for number, line in enumerate(lines):
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
            found.append((number, len(heading.group(1)), heading.group(2).strip()))
    return found


def check_pr_body(text: str) -> list[Problem]:
    """段不在、或段里只有空白，都算问题；有实际内容就没有问题。"""
    lines = text.splitlines()
    headings = _headings(lines)
    target_indexes = [
        index
        for index, (_, level, title) in enumerate(headings)
        if level == 2 and title == SECTION_NAME
    ]

    if not target_indexes:
        return [Problem("PR 描述", "缺「## 人话说明」这一段，补上再跑一次")]

    sections: list[str] = []
    for index in target_indexes:
        start = headings[index][0]
        end = len(lines)
        for number, level, _ in headings[index + 1 :]:
            if level <= 2:
                end = number
                break
        sections.append("\n".join(lines[start + 1 : end]))

    if any(section.strip() for section in sections):
        return []
    return [Problem("PR 描述", "「## 人话说明」这一段是空的，写点人话再跑一次")]
