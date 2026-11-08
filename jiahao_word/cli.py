"""命令行入口：本地和 CI 都从这里跑。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .check import Problem, check_groups
from .check_pr import SECTION_NAME, check_pr_body


def _report_problems(problems: list[Problem]) -> None:
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"共 {len(problems)} 处问题，改完再跑一次。", file=sys.stderr)


def _read_body(body_file: str) -> str:
    if body_file == "-":
        return sys.stdin.read().removeprefix("\ufeff")
    return Path(body_file).read_text(encoding="utf-8-sig")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jiahao-word",
        description="检查词库数据和 PR 描述，一次把所有问题列出来。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="检查组文件里的数据")
    check_parser.add_argument(
        "--groups",
        type=Path,
        default=Path("groups"),
        help="组文件所在目录，默认是 groups",
    )

    check_pr_parser = sub.add_parser(
        "check-pr", help=f"检查 PR 描述里的「{SECTION_NAME}」段"
    )
    check_pr_parser.add_argument(
        "--body-file",
        default="-",
        help="PR 描述文件；写 - 或省略就从标准输入读",
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        problems, group_count = check_groups(args.groups)
        if problems:
            _report_problems(problems)
            return 1
        print(f"检查通过：{group_count} 个组都没问题。")
        return 0

    if args.command == "check-pr":
        try:
            body = _read_body(args.body_file)
        except (OSError, UnicodeDecodeError) as error:
            _report_problems([Problem(args.body_file, f"这个文件读不了：{error}")])
            return 1

        problems = check_pr_body(body)
        if problems:
            _report_problems(problems)
            return 1
        print("人话说明有内容，检查通过。")
        return 0

    return 2
