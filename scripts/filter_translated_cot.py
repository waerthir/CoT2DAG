"""从 JSON 列表中筛选翻译状态为 translated 的完整记录。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STATUS_FIELD = "cot_translation_status"
TRANSLATED_STATUS = "translated"


class FilterInputError(ValueError):
    """输入路径或 JSON 结构不符合筛选要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回筛选脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="保留 JSON 列表中 cot_translation_status 为 translated 的元素。"
    )
    parser.add_argument("input_json", type=Path, help="输入 JSON 文件路径")
    parser.add_argument("output_json", type=Path, help="筛选结果 JSON 文件路径")
    return parser


def validate_paths(input_path: Path, output_path: Path) -> tuple[Path, Path]:
    """解析输入输出路径，并阻止输出覆盖输入文件。"""

    resolved_input = input_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_input == resolved_output:
        raise FilterInputError("输入路径和输出路径不能相同。")
    return resolved_input, resolved_output


def load_items(input_path: Path) -> list[dict[str, Any]]:
    """读取输入 JSON，并验证其顶层列表和元素对象结构。"""

    try:
        source_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FilterInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise FilterInputError(f"输入文件不是合法 JSON：{exc}") from exc

    if not isinstance(source_data, list):
        raise FilterInputError("输入 JSON 顶层必须是列表。")
    if not all(isinstance(item, dict) for item in source_data):
        raise FilterInputError("输入 JSON 列表中的每个元素必须是对象。")
    return source_data


def filter_translated_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按原始顺序保留翻译状态严格等于 translated 的完整元素。"""

    return [
        item
        for item in items
        if item.get(STATUS_FIELD) == TRANSLATED_STATUS
    ]


def write_output_items(output_path: Path, output_items: list[dict[str, Any]]) -> None:
    """将筛选出的完整元素写为 UTF-8 编码、带缩进的 JSON 列表。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def execute(input_path: Path, output_path: Path) -> int:
    """完成读取、筛选、写出，并输出本次筛选摘要。"""

    input_path, output_path = validate_paths(input_path, output_path)
    source_items = load_items(input_path)
    output_items = filter_translated_items(source_items)
    write_output_items(output_path, output_items)
    print(f"输入总数：{len(source_items)}")
    print(f"保留数量：{len(output_items)}")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json, args.output_json)
    except FilterInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
