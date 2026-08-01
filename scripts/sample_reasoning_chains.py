"""从 JSON 或 JSONL 文件中随机抽取推理链，并生成 JSON 批处理输入文件。"""

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
        description="从 JSON 数组或 JSONL 随机抽样或全采样，并生成带 batch_id 的精简 JSON。"
    )
    parser.add_argument("input_json", type=Path, help="源 JSON 或 JSONL 文件路径")
    parser.add_argument("output_json", type=Path, help="抽样结果 JSON 文件路径")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--count",
        type=_non_negative_integer,
        help="随机抽取数量，必须为非负整数",
    )
    mode_group.add_argument(
        "--all",
        dest="all_records",
        action="store_true",
        help="按输入中的有效记录原始顺序输出全部记录",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="仅 --count 模式使用的可选随机种子",
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


def load_source_items(
    input_path: Path, print_skipped: bool = False
) -> tuple[list[dict[str, Any]], int]:
    """读取源文件，保留有效记录并返回累计跳过的坏记录数量。"""

    try:
        if input_path.suffix.lower() == ".json":
            raw_data = json.loads(input_path.read_text(encoding="utf-8"))
            if not isinstance(raw_data, list):
                raise SamplingInputError("输入 JSON 顶层必须是数组")
            raw_items = [
                (f"JSON 第 {index} 项", item)
                for index, item in enumerate(raw_data, start=1)
            ]
            skipped_count = 0
        elif input_path.suffix.lower() == ".jsonl":
            raw_items, skipped_count = _load_jsonl_items(input_path, print_skipped)
        else:
            raise SamplingInputError("输入文件后缀必须是 .json 或 .jsonl")
    except FileNotFoundError as exc:
        raise SamplingInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise SamplingInputError(f"输入文件不是合法 JSON：{exc}") from exc

    items: list[dict[str, Any]] = []
    for location, item in raw_items:
        if not isinstance(item, dict):
            skipped_count += 1
            if print_skipped:
                print(f"跳过 {location}：记录必须是对象")
            continue
        reasoning_chain = item.get("reasoning_chain_model")
        if not isinstance(reasoning_chain, str) or not reasoning_chain.strip():
            skipped_count += 1
            if print_skipped:
                print(f"跳过 {location}：缺少非空 reasoning_chain_model")
            continue
        items.append(item)
    return items, skipped_count


def _load_jsonl_items(
    input_path: Path, print_skipped: bool
) -> tuple[list[tuple[str, Any]], int]:
    """逐行读取 JSONL，跳过空行和无法解析的非空行。"""

    items: list[tuple[str, Any]] = []
    skipped_count = 0
    with input_path.open("r", encoding="utf-8") as source_file:
        for line_number, line in enumerate(source_file, start=1):
            if not line.strip():
                continue
            try:
                items.append((f"JSONL 第 {line_number} 行", json.loads(line)))
            except json.JSONDecodeError:
                skipped_count += 1
                if print_skipped:
                    print(f"跳过 JSONL 第 {line_number} 行：不是合法 JSON")
    return items, skipped_count


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


def build_all_output_items(source_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """按有效记录原始顺序生成全部输出，并按有效记录总数确定编号宽度。"""

    width = len(str(len(source_items)))
    return [
        {
            "batch_id": f"{index:0{width}d}",
            "reasoning_chain_model": item["reasoning_chain_model"],
        }
        for index, item in enumerate(source_items, start=1)
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


def execute(
    input_path: Path,
    output_path: Path,
    count: int | None,
    seed: int | None,
    all_records: bool,
) -> int:
    """完成读取、抽样、写出，并打印本次抽样摘要。"""

    if all_records and seed is not None:
        raise SamplingInputError("--all 模式不接受 --seed")
    if not all_records and count is None:
        raise SamplingInputError("必须指定 --count 或 --all")

    input_path, output_path = validate_paths(input_path, output_path)
    source_items, skipped_count = load_source_items(input_path, print_skipped=all_records)
    output_items = (
        build_all_output_items(source_items)
        if all_records
        else build_output_items(source_items, count, seed)
    )
    write_output_items(output_path, output_items)

    print(f"运行模式：{'全采样' if all_records else '随机抽样'}")
    print(f"有效源记录数：{len(source_items)}")
    print(f"跳过记录数：{skipped_count}")
    if not all_records:
        print(f"请求抽取数：{count}")
    print(f"实际抽取数：{len(output_items)}")
    if not all_records:
        print(f"随机种子：{seed if seed is not None else '未指定'}")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(
            args.input_json,
            args.output_json,
            args.count,
            args.seed,
            args.all_records,
        )
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

---

python scripts\sample_reasoning_chains.py `
  data\cot-1\gemini-3.1pro\ready3_gemini31pro_api777_native_promptA_en_blind_manifest_first3_fixed_20260721.jsonl `
  data\cot-1\gemini-3.1pro\cot.json `
  --count 200 `
  --seed 6666

--- 

python scripts\sample_reasoning_chains.py `
  data\cot-2\gemini-3.1-pro\gemini-3.1-pro-process1.json `
  data\cot-2\gemini-3.1-pro\cot.json `
  --all

'''
