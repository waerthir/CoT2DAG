"""检查 JSON 文件的键和值中是否包含 Unicode 汉字。"""

from __future__ import annotations

import argparse
import json
import math
import unicodedata
from pathlib import Path
from typing import Any


class JsonChineseCheckError(ValueError):
    """输入路径或 JSON 内容无法用于中文检测时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回 JSON 中文检测脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="检查 JSON 文件的键和值中是否包含 Unicode 汉字。"
    )
    parser.add_argument("input_json", type=Path, help="待检查的 JSON 文件路径")
    parser.add_argument(
        "--min-consecutive-han",
        type=_positive_integer,
        default=1,
        help="触发检测所需的最小连续汉字数量，默认值为 1",
    )
    parser.add_argument(
        "--field",
        help="顶层列表元素中需要检测的字符串字段名",
    )
    parser.add_argument(
        "--han-ratio-threshold",
        type=_percentage_threshold,
        help="判定中文项所需严格超过的中文比例阈值，范围为 0 至 100",
    )
    parser.add_argument(
        "--remove-chinese",
        action="store_true",
        help="从过滤输出中移除判定为中文项的完整列表元素",
    )
    parser.add_argument(
        "--filtered-output-json",
        type=Path,
        help="启用 --remove-chinese 时写入保留元素的 JSON 输出路径",
    )
    return parser


def _positive_integer(value: str) -> int:
    """将命令行参数转换为正整数，非法值交给 argparse 报错。"""

    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("连续汉字阈值必须是正整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("连续汉字阈值必须是正整数")
    return number


def _percentage_threshold(value: str) -> float:
    """将命令行参数转换为 0 至 100 范围内的有限百分比。"""

    try:
        threshold = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("中文比例阈值必须是 0 至 100 的数值") from exc
    if not math.isfinite(threshold) or not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("中文比例阈值必须是 0 至 100 的数值")
    return threshold


def load_json(input_path: Path) -> Any:
    """以 UTF-8 读取并解析指定的 JSON 文件。"""

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise JsonChineseCheckError(f"输入文件不存在：{input_path}") from exc
    except OSError as exc:
        raise JsonChineseCheckError(f"输入文件无法读取：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise JsonChineseCheckError(f"输入文件不是合法 JSON：{exc}") from exc


def is_han_character(character: str) -> bool:
    """判断字符是否为当前 Python Unicode 数据库识别的汉字。"""

    character_name = unicodedata.name(character, "")
    return character_name.startswith(
        ("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-")
    )


def find_first_han_sequence(text: str, minimum_length: int) -> str | None:
    """返回字符串中首个达到指定长度的连续汉字段。"""

    current_sequence: list[str] = []
    for character in text:
        if is_han_character(character):
            current_sequence.append(character)
            continue
        if len(current_sequence) >= minimum_length:
            return "".join(current_sequence)
        current_sequence.clear()
    if len(current_sequence) >= minimum_length:
        return "".join(current_sequence)
    return None


def find_first_han_sequence_in_json(
    value: Any, minimum_length: int, path: str = "$"
) -> tuple[str, str] | None:
    """递归查找 JSON 键和值中的首个达标连续汉字段。"""

    if isinstance(value, str):
        sequence = find_first_han_sequence(value, minimum_length)
        if sequence is not None:
            return path, sequence
        return None

    if isinstance(value, list):
        for index, item in enumerate(value):
            result = find_first_han_sequence_in_json(
                item, minimum_length, f"{path}[{index}]"
            )
            if result is not None:
                return result
        return None

    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                sequence = find_first_han_sequence(key, minimum_length)
                if sequence is not None:
                    return f"{path} 的键 {key!r}", sequence
            result = find_first_han_sequence_in_json(
                item, minimum_length, f"{path}[{key!r}]"
            )
            if result is not None:
                return result
    return None


def calculate_han_ratio(text: str) -> float:
    """计算字符串中汉字占全部非空白字符的百分比。"""

    content_characters = [character for character in text if not character.isspace()]
    if not content_characters:
        return 0.0
    han_count = sum(is_han_character(character) for character in content_characters)
    return han_count / len(content_characters) * 100


def find_field_match(
    item: Any, field_name: str, minimum_length: int, ratio_threshold: float
) -> tuple[str, float] | None:
    """检查一个列表元素的指定字段是否同时满足连续汉字和比例阈值。"""

    if not isinstance(item, dict):
        return None
    field_value = item.get(field_name)
    if not isinstance(field_value, str):
        return None

    sequence = find_first_han_sequence(field_value, minimum_length)
    ratio = calculate_han_ratio(field_value)
    if sequence is None or ratio <= ratio_threshold:
        return None
    return sequence, ratio


def write_filtered_json(output_path: Path, items: list[Any]) -> None:
    """将保留元素原子写入指定的 JSON 输出文件。"""

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(output_path)
    except OSError as exc:
        raise JsonChineseCheckError(f"过滤结果无法写入：{output_path}") from exc


def execute_field_mode(
    json_data: list[Any],
    field_name: str,
    minimum_length: int,
    ratio_threshold: float,
    remove_chinese: bool,
    filtered_output_path: Path | None,
    input_path: Path,
) -> int:
    """检测列表元素的指定字段，并按需写出移除中文项后的列表。"""

    matched_count = 0
    retained_items: list[Any] = []
    for index, item in enumerate(json_data):
        result = find_field_match(item, field_name, minimum_length, ratio_threshold)
        if result is None:
            retained_items.append(item)
            continue

        matched_count += 1
        sequence, ratio = result
        print(f"元素索引：{index}")
        print(f"检测字段：{field_name}")
        print(f"检测到中文：{sequence}")
        print(f"连续汉字长度：{len(sequence)}")
        print(f"中文比例：{ratio:.2f}%")

    if matched_count == 0:
        print("未检测到中文。")
    print(f"命中元素数：{matched_count}")
    print(f"总元素数：{len(json_data)}")

    if remove_chinese:
        if filtered_output_path is None:
            raise JsonChineseCheckError("--remove-chinese 必须同时指定 --filtered-output-json")
        resolved_output = filtered_output_path.resolve()
        if resolved_output == input_path:
            raise JsonChineseCheckError("过滤输出路径不能与输入文件相同")
        write_filtered_json(resolved_output, retained_items)
        print(f"过滤后元素数：{len(retained_items)}")
        print(f"过滤结果文件：{resolved_output}")
    return 0


def execute(
    input_path: Path,
    minimum_length: int,
    field_name: str | None,
    ratio_threshold: float | None,
    remove_chinese: bool,
    filtered_output_path: Path | None,
) -> int:
    """读取 JSON、检测中文，并在终端输出检测结果。"""

    resolved_input = input_path.resolve()
    json_data = load_json(resolved_input)
    if field_name is not None:
        if not field_name.strip():
            raise JsonChineseCheckError("--field 必须是非空字段名")
        if ratio_threshold is None:
            raise JsonChineseCheckError("指定 --field 时必须提供 --han-ratio-threshold")
        if filtered_output_path is not None and not remove_chinese:
            raise JsonChineseCheckError(
                "--filtered-output-json 必须配合 --remove-chinese 使用"
            )
        if not isinstance(json_data, list):
            raise JsonChineseCheckError("指定 --field 时输入 JSON 顶层必须是列表")
        return execute_field_mode(
            json_data,
            field_name.strip(),
            minimum_length,
            ratio_threshold,
            remove_chinese,
            filtered_output_path,
            resolved_input,
        )

    if ratio_threshold is not None or remove_chinese or filtered_output_path is not None:
        raise JsonChineseCheckError(
            "--han-ratio-threshold、--remove-chinese 和 --filtered-output-json 需要配合 --field 使用"
        )

    if isinstance(json_data, list):
        match_count = 0
        for index, item in enumerate(json_data):
            result = find_first_han_sequence_in_json(
                item, minimum_length, f"$[{index}]"
            )
            if result is None:
                continue
            match_count += 1
            path, sequence = result
            print(f"元素索引：{index}")
            print(f"检测到中文：{sequence}")
            print(f"连续汉字长度：{len(sequence)}")
            print(f"首次命中位置：{path}")

        if match_count == 0:
            print("未检测到中文。")
        else:
            print(f"命中元素数：{match_count}")
            print(f"总元素数：{len(json_data)}")
        return 0

    result = find_first_han_sequence_in_json(json_data, minimum_length)
    if result is None:
        print("未检测到中文。")
        return 0

    path, sequence = result
    print(f"检测到中文：{sequence}")
    print(f"连续汉字长度：{len(sequence)}")
    print(f"首次命中位置：{path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(
            args.input_json,
            args.min_consecutive_han,
            args.field,
            args.han_ratio_threshold,
            args.remove_chinese,
            args.filtered_output_json,
        )
    except JsonChineseCheckError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
