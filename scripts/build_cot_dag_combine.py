"""按 sample_id 将原始 CoT 与 DAG 图结构拼接为新的 JSON 列表。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class CotDagCombineError(ValueError):
    """输入文件或字段无法安全拼接时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回本脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="按 DAG batch_id 与原始记录 sample_id 拼接 CoT 和图结构。"
    )
    parser.add_argument(
        "--dag-json",
        type=Path,
        required=True,
        help="包含 batch_id 和 graph 的 DAG JSON 路径",
    )
    parser.add_argument(
        "--source-json",
        type=Path,
        required=True,
        help="包含 sample_id 和 reasoning_chain_model 的原始数据 JSON 路径",
    )
    parser.add_argument(
        "--output-json", type=Path, required=True, help="合并结果 JSON 输出路径"
    )
    return parser


def validate_paths(
    dag_path: Path, source_path: Path, output_path: Path
) -> tuple[Path, Path, Path]:
    """解析三个路径，并阻止输出文件覆盖任一输入文件。"""

    resolved_dag = dag_path.resolve()
    resolved_source = source_path.resolve()
    resolved_output = output_path.resolve()
    if resolved_dag == resolved_source:
        raise CotDagCombineError("DAG JSON 路径和原始数据 JSON 路径不能相同。")
    if resolved_output in {resolved_dag, resolved_source}:
        raise CotDagCombineError("输出路径不能覆盖 DAG JSON 或原始数据 JSON。")
    return resolved_dag, resolved_source, resolved_output


def load_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    """读取顶层为对象列表的 JSON 文件。"""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CotDagCombineError(f"{description}不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise CotDagCombineError(f"{description}不是合法 JSON：{path}；{exc}") from exc

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CotDagCombineError(f"{description}必须是由对象组成的 JSON 列表：{path}")
    return value


def require_nonempty_string(value: Any, field_name: str, record_label: str) -> str:
    """读取非空字符串字段，并在字段不符合要求时给出定位信息。"""

    if not isinstance(value, str) or not value.strip():
        raise CotDagCombineError(f"{record_label} 缺少非空字符串字段 {field_name}。")
    return value


def build_dag_index(dag_items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """检查 DAG 必需字段及 batch_id 唯一性，并按 batch_id 建索引。"""

    dag_by_batch_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(dag_items, start=1):
        record_label = f"DAG 第 {index} 条"
        batch_id = require_nonempty_string(item.get("batch_id"), "batch_id", record_label)
        if not isinstance(item.get("graph"), dict):
            raise CotDagCombineError(f"{record_label} 的 graph 必须是对象。")
        if batch_id in dag_by_batch_id:
            raise CotDagCombineError(f"DAG JSON 存在重复 batch_id：{batch_id}")
        dag_by_batch_id[batch_id] = item
    return dag_by_batch_id


def build_source_index(
    source_items: list[dict[str, Any]], target_batch_ids: set[str]
) -> tuple[dict[str, dict[str, Any]], int]:
    """只索引目标 DAG 所需的原始记录，并统计被忽略的额外记录。"""

    source_by_sample_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(source_items, start=1):
        record_label = f"原始记录第 {index} 条"
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or sample_id not in target_batch_ids:
            continue
        require_nonempty_string(
            item.get("reasoning_chain_model"), "reasoning_chain_model", record_label
        )
        if sample_id in source_by_sample_id:
            raise CotDagCombineError(f"原始数据 JSON 存在重复 sample_id：{sample_id}")
        source_by_sample_id[sample_id] = item
    ignored_count = len(source_items) - len(source_by_sample_id)
    return source_by_sample_id, ignored_count


def validate_target_ids(
    dag_by_batch_id: dict[str, dict[str, Any]],
    source_by_sample_id: dict[str, dict[str, Any]],
) -> None:
    """确认每个 DAG batch_id 都能在原始记录中找到对应 sample_id。"""

    missing_in_source = sorted(set(dag_by_batch_id) - set(source_by_sample_id))
    if not missing_in_source:
        return

    raise CotDagCombineError(
        "原始数据中缺少的 DAG batch_id "
        f"（{len(missing_in_source)} 条）：{', '.join(missing_in_source)}"
    )


def build_output_items(
    dag_items: list[dict[str, Any]], source_by_sample_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """按 DAG 原始顺序合并每条图结构与对应的推理链。"""

    output_items: list[dict[str, Any]] = []
    for dag_item in dag_items:
        batch_id = dag_item["batch_id"]
        source_item = source_by_sample_id[batch_id]
        output_items.append(
            {
                "batch_id": batch_id,
                "reasoning_chain_model": source_item["reasoning_chain_model"],
                "graph": dag_item["graph"],
            }
        )
    return output_items


def write_output_items(output_path: Path, output_items: list[dict[str, Any]]) -> None:
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


def execute(dag_path: Path, source_path: Path, output_path: Path) -> int:
    """完成读取、校验、拼接、写入及统计输出。"""

    dag_path, source_path, output_path = validate_paths(
        dag_path, source_path, output_path
    )
    dag_items = load_json_list(dag_path, "DAG JSON")
    source_items = load_json_list(source_path, "原始数据 JSON")
    dag_by_batch_id = build_dag_index(dag_items)
    source_by_sample_id, ignored_source_count = build_source_index(
        source_items, set(dag_by_batch_id)
    )
    validate_target_ids(dag_by_batch_id, source_by_sample_id)
    output_items = build_output_items(dag_items, source_by_sample_id)
    write_output_items(output_path, output_items)

    print(f"DAG 条数：{len(dag_items)}")
    print(f"原始记录条数：{len(source_items)}")
    print(f"合并条数：{len(output_items)}")
    print(f"已忽略的原始记录条数：{ignored_source_count}")
    print(f"输出文件：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.dag_json, args.source_json, args.output_json)
    except CotDagCombineError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
