"""按抽样文件中的 sample_id 筛选源 JSON 记录。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class SourceFilterError(ValueError):
    """抽样文件、源文件或 ID 对应关系不符合要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回本脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="按抽样 sample_id 从源 JSON 的 batch_id 中筛选记录。"
    )
    parser.add_argument(
        "--selection-json",
        type=Path,
        required=True,
        metavar="PATH",
        help="包含 sample_id 的抽样 JSON 路径",
    )
    parser.add_argument(
        "--source-json",
        type=Path,
        required=True,
        metavar="PATH",
        help="包含 batch_id 的源 JSON 路径",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        metavar="PATH",
        help="筛选后子集 JSON 输出路径",
    )
    return parser


def require_nonempty_string(value: Any, field_name: str, record_label: str) -> str:
    """读取记录中的非空字符串字段，并在无效时给出定位信息。"""

    if not isinstance(value, str) or not value.strip():
        raise SourceFilterError(f"{record_label} 缺少非空字符串字段 {field_name}。")
    return value


def validate_paths(
    selection_path: Path, source_path: Path, output_path: Path
) -> tuple[Path, Path, Path]:
    """解析三个路径，并阻止输入互相混用或输出覆盖输入。"""

    resolved_selection = selection_path.resolve()
    resolved_source = source_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_selection == resolved_source:
        raise SourceFilterError("抽样 JSON 路径和源 JSON 路径不能相同。")
    if resolved_output in {resolved_selection, resolved_source}:
        raise SourceFilterError("输出路径不能覆盖抽样 JSON 或源 JSON。")
    return resolved_selection, resolved_source, resolved_output


def load_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    """读取顶层为对象列表的 JSON 文件。"""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SourceFilterError(f"{description}不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SourceFilterError(f"{description}不是合法 JSON：{path}；{exc}") from exc

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SourceFilterError(f"{description}必须是由对象组成的 JSON 列表：{path}")
    return value


def build_selection_ids(selection_items: list[dict[str, Any]]) -> set[str]:
    """读取唯一的抽样 sample_id 集合。"""

    selection_ids: set[str] = set()
    for index, item in enumerate(selection_items, start=1):
        sample_id = require_nonempty_string(
            item.get("sample_id"), "sample_id", f"抽样记录第 {index} 条"
        )
        if sample_id in selection_ids:
            raise SourceFilterError(f"抽样 JSON 存在重复 sample_id：{sample_id}")
        selection_ids.add(sample_id)
    return selection_ids


def build_source_index(source_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """检查源 batch_id 唯一性，并按 batch_id 建立索引。"""

    source_by_batch_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(source_items, start=1):
        batch_id = require_nonempty_string(
            item.get("batch_id"), "batch_id", f"源记录第 {index} 条"
        )
        if batch_id in source_by_batch_id:
            raise SourceFilterError(f"源 JSON 存在重复 batch_id：{batch_id}")
        source_by_batch_id[batch_id] = item
    return source_by_batch_id


def validate_selection_coverage(
    selection_ids: set[str], source_by_batch_id: dict[str, dict[str, Any]]
) -> None:
    """确认每个抽样 sample_id 都能在源 batch_id 中找到。"""

    missing_ids = sorted(selection_ids - set(source_by_batch_id))
    if missing_ids:
        raise SourceFilterError(
            f"源 JSON 中缺少 {len(missing_ids)} 个抽样 sample_id："
            f"{', '.join(missing_ids)}"
        )


def build_output_items(
    source_items: list[dict[str, Any]], selection_ids: set[str]
) -> list[dict[str, Any]]:
    """按源文件原始顺序保留 batch_id 被抽中的完整源记录。"""

    return [item for item in source_items if item["batch_id"] in selection_ids]


def write_output(output_path: Path, output_items: list[dict[str, Any]]) -> None:
    """先写入同目录临时文件，再原子替换为正式输出文件。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(output_items, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def execute(selection_path: Path, source_path: Path, output_path: Path) -> int:
    """完成读取、ID 校验、源记录筛选、写出与统计提示。"""

    selection_path, source_path, output_path = validate_paths(
        selection_path, source_path, output_path
    )
    selection_items = load_json_list(selection_path, "抽样 JSON")
    source_items = load_json_list(source_path, "源 JSON")
    selection_ids = build_selection_ids(selection_items)
    source_by_batch_id = build_source_index(source_items)
    validate_selection_coverage(selection_ids, source_by_batch_id)
    output_items = build_output_items(source_items, selection_ids)
    write_output(output_path, output_items)

    print(f"抽样 ID 数：{len(selection_ids)}")
    print(f"源记录数：{len(source_items)}")
    print(f"输出记录数：{len(output_items)}")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.selection_json, args.source_json, args.output_json)
    except SourceFilterError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
