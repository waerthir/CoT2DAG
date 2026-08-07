"""统计固定 CoT 翻译结果文件中的 cot_translation_status 分布。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


INPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "cot-3"
    / "gemini-3.1-pro-process1_translated.json"
)
STATUS_FIELD = "cot_translation_status"


class StatusCountInputError(ValueError):
    """统计文件不存在或 JSON 结构不符合预期时抛出的异常。"""


def load_items(input_path: Path) -> list[dict[str, Any]]:
    """读取固定输入文件，并验证顶层列表及列表元素对象结构。"""

    try:
        source_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StatusCountInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise StatusCountInputError(f"输入文件不是合法 JSON：{exc}") from exc

    if not isinstance(source_data, list):
        raise StatusCountInputError("输入 JSON 顶层必须是列表。")
    if not all(isinstance(item, dict) for item in source_data):
        raise StatusCountInputError("输入 JSON 列表中的每个元素必须是对象。")
    return source_data


def count_statuses(items: list[dict[str, Any]]) -> tuple[Counter[str], int]:
    """统计状态字段的各个字符串取值，并返回缺失字段的元素数量。"""

    status_counts: Counter[str] = Counter()
    missing_count = 0
    for index, item in enumerate(items, start=1):
        if STATUS_FIELD not in item:
            missing_count += 1
            continue

        status = item[STATUS_FIELD]
        if not isinstance(status, str):
            raise StatusCountInputError(
                f"第 {index} 个元素的 {STATUS_FIELD} 必须是字符串。"
            )
        status_counts[status] += 1
    return status_counts, missing_count


def print_summary(
    total_count: int, status_counts: Counter[str], missing_count: int
) -> None:
    """将总数、字段覆盖数、缺失数和按状态排序的统计结果输出到终端。"""

    present_count = total_count - missing_count
    print(f"总记录数：{total_count}")
    print(f"具有 {STATUS_FIELD} 字段的记录数：{present_count}")
    print(f"缺少 {STATUS_FIELD} 字段的记录数：{missing_count}")
    print("状态统计：")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


def main() -> int:
    """执行固定文件的状态统计，并将预期输入错误转换为退出码 2。"""

    try:
        items = load_items(INPUT_PATH)
        status_counts, missing_count = count_statuses(items)
        print_summary(len(items), status_counts, missing_count)
    except StatusCountInputError as exc:
        print(f"错误：{exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
