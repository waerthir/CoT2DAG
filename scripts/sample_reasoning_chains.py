"""从大 JSON 文件中随机抽取推理链，并生成可直接用于批处理的输入文件。"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


class SamplingInputError(ValueError):
    """输入路径、数量或 JSON 内容不符合抽样要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回随机抽样脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="从 JSON 数组随机抽取推理链，并生成带 batch_id 的精简 JSON。"
    )
    parser.add_argument("input_json", type=Path, help="源 JSON 文件路径")
    parser.add_argument("output_json", type=Path, help="抽样结果 JSON 文件路径")
    parser.add_argument(
        "--count",
        type=_non_negative_integer,
        required=True,
        help="请求抽取数量，必须为非负整数",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="可选随机种子；提供后抽样结果可复现",
    )
    return parser


def _non_negative_integer(value: str) -> int:
    """将命令行字符串转换为非负整数；非法值交给 argparse 报错。"""

    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("数量必须是非负整数") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("数量必须是非负整数")
    return number


def load_source_items(input_path: Path) -> list[dict[str, Any]]:
    """读取源 JSON 数组，并验证每个元素都有非空 reasoning_chain_model。"""

    try:
        raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SamplingInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise SamplingInputError(f"输入文件不是合法 JSON：{exc}") from exc

    if not isinstance(raw_data, list):
        raise SamplingInputError("输入 JSON 顶层必须是数组")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw_data):
        if not isinstance(item, dict):
            raise SamplingInputError(f"输入第 {index} 项必须是对象")
        reasoning_chain = item.get("reasoning_chain_model")
        if not isinstance(reasoning_chain, str) or not reasoning_chain.strip():
            raise SamplingInputError(
                f"输入第 {index} 项缺少非空字符串 reasoning_chain_model"
            )
        items.append(item)
    return items


def build_output_items(
    source_items: list[dict[str, Any]], count: int, seed: int | None
) -> list[dict[str, str]]:
    """按请求数量随机抽样，并生成连续的字符串 batch_id。"""

    actual_count = min(count, len(source_items))
    # 独立随机生成器避免影响或依赖其他代码的全局随机状态。
    random_generator = random.Random(seed)
    sampled_items = random_generator.sample(source_items, actual_count)
    # 宽度按用户请求数量确定；例如请求 100 条时使用 001、002……。
    width = len(str(count))

    return [
        {
            "batch_id": f"{index:0{width}d}",
            "reasoning_chain_model": item["reasoning_chain_model"],
        }
        for index, item in enumerate(sampled_items, start=1)
    ]


def write_output_items(output_path: Path, output_items: list[dict[str, str]]) -> None:
    """将抽样结果先写入临时文件，再原子替换目标输出文件。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(output_path)


def validate_paths(input_path: Path, output_path: Path) -> tuple[Path, Path]:
    """解析输入输出路径，并阻止输出文件覆盖源文件。"""

    resolved_input = input_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_input == resolved_output:
        raise SamplingInputError("输入路径和输出路径不能相同")
    return resolved_input, resolved_output


def execute(input_path: Path, output_path: Path, count: int, seed: int | None) -> int:
    """完成读取、抽样、写出，并打印本次抽样摘要。"""

    input_path, output_path = validate_paths(input_path, output_path)
    source_items = load_source_items(input_path)
    output_items = build_output_items(source_items, count, seed)
    write_output_items(output_path, output_items)

    print(f"源文件元素数：{len(source_items)}")
    print(f"请求抽取数：{count}")
    print(f"实际抽取数：{len(output_items)}")
    print(f"随机种子：{seed if seed is not None else '未指定'}")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json, args.output_json, args.count, args.seed)
    except SamplingInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())



'''
python scripts/sample_reasoning_chains.py `
  data\cot-1\llava-cot-11b\output_cot_llava_cot_11b_english6000.json `
  data\cot-1\llava-cot-11b\cot.json `
  --count 200 `
  --seed 6666
'''