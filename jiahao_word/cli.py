"""命令行入口：本地和 CI 都从这里跑。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .check import check_groups


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jiahao-word",
        description="检查词库数据，一次把所有问题列出来。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="检查组文件里的数据")
    check_parser.add_argument(
        "--groups",
        type=Path,
        default=Path("groups"),
        help="组文件所在目录，默认是 groups",
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        problems, group_count = check_groups(args.groups)
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            print(f"共 {len(problems)} 处问题，改完再跑一次。", file=sys.stderr)
            return 1
        print(f"检查通过：{group_count} 个组都没问题。")
        return 0

    return 2
