"""为 JSON 列表中的每条记录生成独立且可追溯的 batch_id。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class UniqueBatchIdInputError(ValueError):
    """输入路径或 JSON 内容不符合 batch_id 独立化要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回 batch_id 独立化脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="为 JSON 列表中每条记录的 batch_id 追加唯一行序号。"
    )
    parser.add_argument("input_json", type=Path, help="输入 JSON 文件路径")
    parser.add_argument("output_json", type=Path, help="输出 JSON 文件路径")
    return parser


def validate_paths(input_path: Path, output_path: Path) -> tuple[Path, Path]:
    """解析输入输出路径，并阻止输出文件覆盖输入文件。"""

    resolved_input = input_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_input == resolved_output:
        raise UniqueBatchIdInputError("输入路径和输出路径不能相同。")
    return resolved_input, resolved_output


def load_source_items(input_path: Path) -> list[dict[str, Any]]:
    """读取输入 JSON，并验证顶层列表及其元素对象结构。"""

    try:
        source_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UniqueBatchIdInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise UniqueBatchIdInputError(f"输入文件不是合法 JSON：{exc}") from exc

    if not isinstance(source_data, list):
        raise UniqueBatchIdInputError("输入 JSON 顶层必须是列表。")
    if not all(isinstance(item, dict) for item in source_data):
        raise UniqueBatchIdInputError("输入 JSON 列表中的每个元素必须是对象。")
    return source_data


def build_output_items(source_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """复制完整记录，并用原 ID 与一基行序号组成新的唯一 batch_id。"""

    output_items: list[dict[str, Any]] = []
    for index, item in enumerate(source_items, start=1):
        original_batch_id = item.get("batch_id")
        if not isinstance(original_batch_id, str) or not original_batch_id.strip():
            raise UniqueBatchIdInputError(
                f"第 {index} 个元素的 batch_id 必须是非空字符串。"
            )

        output_item = dict(item)
        output_item["batch_id"] = f"{original_batch_id}__row_{index:06d}"
        output_items.append(output_item)
    return output_items


def write_output_items(output_path: Path, output_items: list[dict[str, Any]]) -> None:
    """将独立化后的完整记录写为 UTF-8 编码、带缩进的 JSON 列表。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def execute(input_path: Path, output_path: Path) -> int:
    """完成路径检查、读取、batch_id 改写、写出与结果提示。"""

    input_path, output_path = validate_paths(input_path, output_path)
    source_items = load_source_items(input_path)
    output_items = build_output_items(source_items)
    write_output_items(output_path, output_items)
    print(f"已独立化 {len(output_items)} 条记录的 batch_id。")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json, args.output_json)
    except UniqueBatchIdInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
