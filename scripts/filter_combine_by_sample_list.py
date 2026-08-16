"""按共同样本名单顺序切分单个模型的 combine JSON。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class CombineFilterError(ValueError):
    """名单或 combine 数据不符合切分要求时抛出。"""


def build_parser() -> argparse.ArgumentParser:
    """构造三个位置参数的命令行解析器。"""

    parser = argparse.ArgumentParser(description="按共同样本名单切分 combine JSON")
    parser.add_argument("sample_list_json", type=Path, help="含 selected_items 的共同样本名单 JSON")
    parser.add_argument("source_combine_json", type=Path, help="单个模型的源 combine JSON")
    parser.add_argument("output_json", type=Path, help="切分后的 combine JSON 输出路径")
    return parser


def _load_json(path: Path, description: str) -> Any:
    """读取 JSON 文件并转换常见文件错误。"""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CombineFilterError(f"{description}不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise CombineFilterError(f"{description}不是合法 JSON：{path}；{exc}") from exc


def _nonempty_batch_id(item: dict[str, Any], source: str) -> str:
    """从对象中取得非空 batch_id。"""

    batch_id = item.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        raise CombineFilterError(f"{source}的 batch_id 必须是非空字符串。")
    return batch_id


def load_sample_batch_ids(sample_list_path: Path) -> list[str]:
    """读取名单的有序且唯一 batch_id 列表。"""

    data = _load_json(sample_list_path, "共同样本名单")
    if not isinstance(data, dict):
        raise CombineFilterError("共同样本名单顶层必须是对象。")
    selected_items = data.get("selected_items")
    if not isinstance(selected_items, list) or not selected_items:
        raise CombineFilterError("共同样本名单的 selected_items 必须是非空列表。")

    batch_ids: list[str] = []
    seen_batch_ids: set[str] = set()
    for index, item in enumerate(selected_items):
        if not isinstance(item, dict):
            raise CombineFilterError(f"名单 selected_items 第 {index} 条必须是对象。")
        batch_id = _nonempty_batch_id(item, f"名单 selected_items 第 {index} 条")
        if batch_id in seen_batch_ids:
            raise CombineFilterError(f"共同样本名单中存在重复 batch_id：{batch_id}")
        seen_batch_ids.add(batch_id)
        batch_ids.append(batch_id)
    return batch_ids


def load_combine_records(source_path: Path) -> dict[str, dict[str, Any]]:
    """读取源 combine JSON，并建立 batch_id 到完整记录的映射。"""

    data = _load_json(source_path, "源 combine 文件")
    if not isinstance(data, list):
        raise CombineFilterError("源 combine 文件顶层必须是列表。")

    records_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise CombineFilterError(f"源 combine 文件第 {index} 条必须是对象。")
        batch_id = _nonempty_batch_id(item, f"源 combine 文件第 {index} 条")
        if batch_id in records_by_id:
            raise CombineFilterError(f"源 combine 文件中存在重复 batch_id：{batch_id}")
        records_by_id[batch_id] = item
    return records_by_id


def filter_records(
    sample_batch_ids: list[str], records_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """按名单顺序取得完整源记录；先一次性报告所有缺失 ID。"""

    missing_batch_ids = [batch_id for batch_id in sample_batch_ids if batch_id not in records_by_id]
    if missing_batch_ids:
        formatted_ids = "\n".join(f"- {batch_id}" for batch_id in missing_batch_ids)
        raise CombineFilterError(
            f"源 combine 文件缺少 {len(missing_batch_ids)} 个名单 batch_id：\n{formatted_ids}"
        )
    return [records_by_id[batch_id] for batch_id in sample_batch_ids]


def write_json(output_path: Path, records: list[dict[str, Any]]) -> None:
    """通过临时文件原子写入切分结果。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)


def main() -> int:
    """读取名单与源 combine 文件，输出严格对齐的子集。"""

    args = build_parser().parse_args()
    try:
        sample_batch_ids = load_sample_batch_ids(args.sample_list_json)
        records_by_id = load_combine_records(args.source_combine_json)
        records = filter_records(sample_batch_ids, records_by_id)
        write_json(args.output_json, records)
    except CombineFilterError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    ignored_count = len(records_by_id) - len(records)
    print(
        f"名单数={len(sample_batch_ids)}，输出数={len(records)}，"
        f"已忽略源记录数={ignored_count}：{args.output_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
