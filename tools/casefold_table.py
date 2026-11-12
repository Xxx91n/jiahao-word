"""生成查词页要用的归一化表和空白字符表。

页面必须和 jiahao_word/check.py 的 normalize_word 算出同一个键：去掉首尾
空格，英文按 Python str.casefold() 折叠。JS 没有这两套规则，这里把结果算
出来嵌进页面。

这两张表跟着跑它的那个 Python 版本走：不同 Python 版本的 Unicode 数据不
一样。实测：3.11 和 3.12、3.13 一致，3.10 差 40 个码点，3.14 差 27 个码点。
仓库和 CI 都用 3.11，pyproject.toml 把范围钉成 >=3.11,<3.14，所以按 3.11
的规则生成。真要在更高版本上支持，得按新版本的规则重算这张表。

改了规则或换了 Python 版本后重新跑一次，再把 api/index.html 一起提交：

    python tools/casefold_table.py

只重写 api/index.html 里 <generated> 和 </generated> 之间的内容。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE = REPO_ROOT / "api" / "index.html"
START_MARKER = "// <generated>"
END_MARKER = "// </generated>"


def fold_pairs() -> dict[str, str]:
    """casefold 之后和原字符不一样的那些字符。"""
    pairs: dict[str, str] = {}
    for point in range(0x110000):
        if 0xD800 <= point <= 0xDFFF:
            continue
        char = chr(point)
        folded = char.casefold()
        if folded != char:
            pairs[char] = folded
    return pairs


def whitespace_chars() -> list[str]:
    """Python str.strip() 会去掉的空白字符。"""
    return [
        chr(point)
        for point in range(0x110000)
        if not (0xD800 <= point <= 0xDFFF) and chr(point).isspace()
    ]


def render_fold(pairs: dict[str, str]) -> str:
    """排好序、一行十条，方便看 diff。"""
    items = [
        json.dumps({key: pairs[key]}, ensure_ascii=False, separators=(",", ":"))[1:-1]
        for key in sorted(pairs)
    ]
    rows = [",".join(items[index : index + 10]) for index in range(0, len(items), 10)]
    return "var CASE_FOLD = {\n  " + ",\n  ".join(rows) + "\n};"


def render_whitespace(chars: list[str]) -> str:
    return "var WHITESPACE = [" + ",".join(json.dumps(char) for char in chars) + "];"


def main() -> int:
    text = PAGE.read_text(encoding="utf-8")
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        print(f"页面里要正好有一个 {START_MARKER} 和一个 {END_MARKER}", file=sys.stderr)
        return 1

    pairs = fold_pairs()
    whitespace = whitespace_chars()
    body = "\n" + render_fold(pairs) + "\n" + render_whitespace(whitespace)
    start = text.index(START_MARKER) + len(START_MARKER)
    end = text.index(END_MARKER)
    text = text[:start] + body + "\n" + text[end:]
    PAGE.write_text(text, encoding="utf-8", newline="\n")
    print(f"写了 {len(pairs)} 条 casefold 和 {len(whitespace)} 个空白字符")
    return 0


if __name__ == "__main__":
    sys.exit(main())
