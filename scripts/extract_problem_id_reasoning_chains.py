"""从原始 JSON 列表提取 problem_id 与推理链，生成批处理 CoT 输入文件。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class ExtractionInputError(ValueError):
    """输入路径或输入 JSON 内容不符合提取要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回本脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="从 JSON 列表提取 problem_id 和 reasoning_chain_model。"
    )
    parser.add_argument("input_json", type=Path, help="原始 JSON 文件路径")
    parser.add_argument("output_json", type=Path, help="输出 JSON 文件路径")
    return parser


def validate_paths(input_path: Path, output_path: Path) -> tuple[Path, Path]:
    """解析输入输出路径，并阻止输出文件覆盖输入文件。"""

    resolved_input = input_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_input == resolved_output:
        raise ExtractionInputError("输入路径和输出路径不能相同。")
    return resolved_input, resolved_output


def load_source_items(input_path: Path) -> list[dict[str, Any]]:
    """读取并检查顶层为列表、且元素均为对象的源 JSON 文件。"""

    try:
        source_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExtractionInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ExtractionInputError(f"输入文件不是合法 JSON：{exc}") from exc

    if not isinstance(source_data, list):
        raise ExtractionInputError("输入 JSON 顶层必须是列表。")
    if not all(isinstance(item, dict) for item in source_data):
        raise ExtractionInputError("输入 JSON 列表中的每个元素必须是对象。")
    return source_data


def build_output_items(source_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """按原顺序将 problem_id 重命名为 batch_id，并保留推理链内容。"""

    output_items: list[dict[str, str]] = []
    for index, item in enumerate(source_items, start=1):
        problem_id = item.get("problem_id")
        reasoning_chain = item.get("reasoning_chain_model")
        if not isinstance(problem_id, str):
            raise ExtractionInputError(
                f"第 {index} 个元素的 problem_id 必须是字符串。"
            )
        if not isinstance(reasoning_chain, str):
            raise ExtractionInputError(
                f"第 {index} 个元素的 reasoning_chain_model 必须是字符串。"
            )
        output_items.append(
            {
                "batch_id": problem_id,
                "reasoning_chain_model": reasoning_chain,
            }
        )
    return output_items


def write_output_items(output_path: Path, output_items: list[dict[str, str]]) -> None:
    """将提取结果写为 UTF-8 编码、带缩进的 JSON 数组。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def execute(input_path: Path, output_path: Path) -> int:
    """完成路径检查、读取、字段提取、写出与结果提示。"""

    input_path, output_path = validate_paths(input_path, output_path)
    source_items = load_source_items(input_path)
    output_items = build_output_items(source_items)
    write_output_items(output_path, output_items)
    print(f"已提取 {len(output_items)} 条记录。")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json, args.output_json)
    except ExtractionInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
