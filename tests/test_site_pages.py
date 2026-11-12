"""静态检查网页查词页：一个文件、内联、相对路径取数、该有的文案都在。"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PAGE = REPO_ROOT / "api" / "index.html"
ROOT_PAGE = REPO_ROOT / "index.html"
REPO_URL = "https://github.com/Xxx91n/jiahao-word"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def script_of(text: str) -> str:
    """取出内联脚本那一段，免得在 HTML 别处匹配到同名文字。"""
    return text[text.index("<script>") : text.index("</script>")]


def test_api_page_is_a_single_file_with_inline_style_and_script() -> None:
    """样式和脚本都在这一个文件里，不引外部框架，也不用编译。"""
    text = read(API_PAGE)

    assert "<style>" in text
    assert "<script>" in text
    assert "<script src=" not in text
    assert not re.search(r'<link[^>]*rel="stylesheet"', text)


def test_api_page_loads_nothing_from_the_network_but_github_links() -> None:
    """除了页面自己拼的 GitHub 链接，不向别的域名取任何东西。"""
    text = read(API_PAGE)
    outside = text.replace(REPO_URL, "")

    assert "http://" not in outside
    assert "https://" not in outside


def test_api_page_reads_relative_data_and_no_absolute_path() -> None:
    """取数据用 ./data.json，不写死 /api/ 这种绝对路径。"""
    script = script_of(read(API_PAGE))

    assert 'fetch("./data.json"' in script
    assert '"/api/' not in script
    assert "'/api/" not in script


def test_api_page_stacks_the_form_on_narrow_screens() -> None:
    """窄屏下表单改成单列，否则按钮会跑到视口外，页面横向滚动。"""
    text = read(API_PAGE)

    assert "grid-template-columns: 1fr auto auto;" in text
    assert "@media (max-width: 30rem)" in text
    media_start = text.index("@media (max-width: 30rem)")
    media_body = text[media_start : text.index("}", text.index("{", media_start))]
    assert "grid-template-columns: 1fr;" in media_body


def test_api_page_reads_word_and_lang_from_the_query() -> None:
    """从网址读 ?word= 和 ?lang=；lang 只认 en，别的都当中文。"""
    text = read(API_PAGE)

    assert 'params.get("word")' in text
    assert 'params.get("lang")' in text
    assert 'raw === "en" ? "en" : "zh"' in text


def test_api_page_normalizes_the_input_the_same_way_as_the_data() -> None:
    """查表前去掉首尾空格，英文按 Python casefold 的规则折叠。"""
    script = script_of(read(API_PAGE))

    assert "stripWhitespace(String(raw" in script
    assert "foldEnglish(text)" in script
    assert "CASE_FOLD" in script


def generated_constants() -> tuple[dict[str, str], list[str]]:
    """把页面 <generated> 段里的两张表抠出来。"""
    text = read(API_PAGE)
    start = text.index("// <generated>")
    end = text.index("// </generated>")

    fold_start = text.index("var CASE_FOLD = ", start) + len("var CASE_FOLD = ")
    fold_end = text.index("};", fold_start) + 1
    table = json.loads(text[fold_start:fold_end])

    space_start = text.index("var WHITESPACE = ", fold_start) + len("var WHITESPACE = ")
    space_end = text.index("];", space_start) + 1
    spaces = json.loads(text[space_start:space_end])

    assert start < fold_start < fold_end < space_end < end
    return table, spaces


def test_page_case_fold_matches_python_over_every_codepoint() -> None:
    """页面折叠每个字符的结果，和 Python str.casefold() 完全一样。

    页面不留兜底：不查表就等于不动。所以缺一条真字符就一定查不到词，
    这里逐码点比对就是查这件事。
    """
    table, _ = generated_constants()

    mismatches = []
    for point in range(0x110000):
        if 0xD800 <= point <= 0xDFFF:
            continue
        char = chr(point)
        if table.get(char, char) != char.casefold():
            mismatches.append((hex(point), char.casefold(), table.get(char)))

    assert mismatches == [], f"有 {len(mismatches)} 个字符对不上，前几个：{mismatches[:5]}"


def test_page_whitespace_matches_python_strip() -> None:
    """页面去掉的空白字符，和 Python strip() 去掉的是同一批。"""
    _, spaces = generated_constants()
    expected = {
        chr(point)
        for point in range(0x110000)
        if not (0xD800 <= point <= 0xDFFF) and chr(point).isspace()
    }

    assert set(spaces) == expected, f"多出来的：{set(spaces) - expected}，少了的：{expected - set(spaces)}"


def test_generated_constants_are_in_sync_with_the_tool(monkeypatch) -> None:
    """页面里的表，和 tools/casefold_table.py 现在会算出来的一致。"""
    table, spaces = generated_constants()

    monkeypatch.syspath_prepend(str(REPO_ROOT / "tools"))
    import casefold_table

    assert table == casefold_table.fold_pairs()
    assert spaces == casefold_table.whitespace_chars()


def test_api_page_has_the_empty_language_and_missing_word_messages() -> None:
    """某门语言没说法、整词查不到，都有明确文案，不留白。"""
    text = read(API_PAGE)

    assert "这个语言暂时没说法" in text
    assert "库里还没有这个词" in text


def function_body(name: str) -> str:
    """按花括号配对，抠出一个函数的完整函数体。"""
    script = script_of(read(API_PAGE))
    start = script.index(f"function {name}(")
    depth = 0
    for position in range(script.index("{", start), len(script)):
        if script[position] == "{":
            depth += 1
        elif script[position] == "}":
            depth -= 1
            if depth == 0:
                return script[start : position + 1]
    raise AssertionError(f"{name} 的花括号没配对，脚本读坏了")


def test_api_page_checks_the_other_language_before_saying_the_word_is_missing() -> None:
    """按一门语言查不到时，先看另一门有没有，别把「这个语言没有」说成「库里没有」。"""
    body = function_body("showMissing")

    assert "otherLanguages(lang).forEach" in body
    assert body.index("elsewhere.length > 0") < body.index("库里还没有这个词")
    assert "?word=" in body and "&lang=" in body


def test_api_page_looks_up_the_other_language_with_the_raw_word() -> None:
    """查另一门语言时按那门语言自己的规则归一化，不能拿这门语言算好的键去查。

    英文页输入 BITE，键已经折成 bite；直接拿 bite 去查中文索引会漏，
    中文的键是不折的 BITE。
    """
    body = function_body("showMissing")

    assert "normalizeQuery(other, original)" in body
    assert "normalizeQuery(other, word)" not in body


def test_api_page_offers_the_new_entry_link_where_the_word_is_really_missing() -> None:
    """只有「两门语言都没有」才给开新词入口；另一门有词时不该让人提重复词。"""
    body = function_body("showMissing")
    script = script_of(read(API_PAGE))

    assert "function appendNewEntryLink(box)" in script
    assert body.count("appendNewEntryLink(box)") == 1
    # 入口要在跨语言那条 return 之后，也就是只挂在「真没有」这条路上。
    assert body.index("appendNewEntryLink(box)") > body.index("elsewhere.length > 0")
    assert body.rindex("return;") < body.index("appendNewEntryLink(box)")


def test_api_page_says_the_word_is_missing_without_guessing() -> None:
    """查不到就说没收录，不再回头补一句「可能是你打错了」。"""
    body = function_body("showMissing")

    assert "库里还没有这个词" in body
    assert "打错" not in body


def test_api_page_builds_issue_links_itself_and_points_at_the_template() -> None:
    """issue 链接由页面拼出来，查不到时给一条开新词的入口。"""
    text = read(API_PAGE)

    assert '"/issues/" + issue' in text
    assert REPO_ROOT.joinpath(".github/ISSUE_TEMPLATE/new-entry.yml").is_file()
    assert "/issues/new?template=new-entry.yml" in text


def test_api_page_shows_every_group_in_numeric_order() -> None:
    """候选全列出来，按组号数字大小排；不挑「最合适的一条」。"""
    text = read(API_PAGE)

    assert "groupNumber(a && a.group) - groupNumber(b && b.group)" in text


def test_api_page_open_without_a_word_does_not_call_the_data() -> None:
    """没带词时只提示怎么用，不去取数据；数据是空的也不会白屏。"""
    script = script_of(read(API_PAGE))
    start = script.index('(function start()')
    body = script[start:]

    assert "if (!word)" in body
    assert body.index("if (!word)") < body.index("lookUp(word, lang, rawWord)")
    assert "return;" in body[: body.index("lookUp(word, lang, rawWord)")]


def test_root_page_points_at_the_api_page_and_the_repo() -> None:
    """根首页只指路：链到 api/ 和仓库主页。"""
    text = read(ROOT_PAGE)

    assert 'href="api/"' in text
    assert REPO_URL in text
    assert text.count("<a ") == 2
