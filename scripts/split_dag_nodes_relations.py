"""将 DAG 文件与 CoT 源文件拆分为节点 JSON 和关系 JSON。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SplitInputError(ValueError):
    """输入文件、路径或 DAG 结构不符合拆分要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回 DAG 拆分脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="将 DAG 文件拆分为节点 JSON 和关系 JSON。"
    )
    parser.add_argument("dag_input_json", type=Path, help="DAG 输入 JSON 路径")
    parser.add_argument("cot_input_json", type=Path, help="CoT 源 JSON 路径")
    parser.add_argument("nodes_output_json", type=Path, help="节点 JSON 输出路径")
    parser.add_argument("relations_output_json", type=Path, help="关系 JSON 输出路径")
    return parser


def resolve_project_path(path: Path) -> Path:
    """将相对路径按项目根目录解析，绝对路径保持不变。"""

    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def validate_distinct_paths(paths: list[Path]) -> None:
    """确保两个输入和两个输出路径两两不同，避免覆盖任一文件。"""

    if len(set(paths)) != len(paths):
        raise SplitInputError("DAG 输入、CoT 输入和两个输出路径必须两两不同")


def load_json_array(path: Path, label: str) -> list[Any]:
    """以 UTF-8 读取 JSON，并要求其顶层结构为数组。"""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SplitInputError(f"{label}文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SplitInputError(f"{label}文件不是合法 JSON：{exc}") from exc
    if not isinstance(data, list):
        raise SplitInputError(f"{label}文件顶层必须是数组")
    return data


def load_cot_by_batch_id(path: Path) -> dict[str, str]:
    """读取 CoT 源文件，建立 batch_id 到完整 reasoning_chain_model 的映射。"""

    cot_by_batch_id: dict[str, str] = {}
    for index, item in enumerate(load_json_array(path, "CoT 源")):
        if not isinstance(item, dict):
            raise SplitInputError(f"CoT 源第 {index} 项必须是对象")
        batch_id = item.get("batch_id")
        reasoning_chain = item.get("reasoning_chain_model")
        if not isinstance(batch_id, str) or not batch_id:
            raise SplitInputError(f"CoT 源第 {index} 项缺少非空字符串 batch_id")
        if not isinstance(reasoning_chain, str) or not reasoning_chain:
            raise SplitInputError(
                f"CoT 源第 {index} 项缺少非空字符串 reasoning_chain_model"
            )
        cot_by_batch_id[batch_id] = reasoning_chain
    return cot_by_batch_id


def split_dag_records(
    dag_records: list[Any], cot_by_batch_id: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按 DAG 输入顺序生成节点记录和以 I/O 为子节点的关系记录。"""

    node_records: list[dict[str, Any]] = []
    relation_records: list[dict[str, Any]] = []
    graph_batch_ids: set[str] = set()

    for graph_index, graph_record in enumerate(dag_records):
        graph_batch_id, graph_logic = validate_graph_record(graph_record, graph_index)
        if graph_batch_id in graph_batch_ids:
            raise SplitInputError(f"DAG 第 {graph_index} 项的 batch_id 重复：{graph_batch_id}")
        graph_batch_ids.add(graph_batch_id)

        try:
            reasoning_chain = cot_by_batch_id[graph_batch_id]
        except KeyError as exc:
            raise SplitInputError(
                f"CoT 源文件中没有 DAG batch_id={graph_batch_id} 对应的推理链"
            ) from exc

        ordered_nodes, lookup = collect_graph_nodes(graph_logic, graph_batch_id)
        node_records.extend(
            build_node_record(graph_batch_id, node, reasoning_chain) for node in ordered_nodes
        )
        relation_records.extend(
            build_relation_record(graph_batch_id, node, lookup, reasoning_chain)
            for node in [
                *graph_logic["intermediate_steps"],
                graph_logic["final_conclusion"],
            ]
        )

    return node_records, relation_records


def validate_graph_record(graph_record: Any, graph_index: int) -> tuple[str, dict[str, Any]]:
    """读取一条 DAG 记录的 batch_id 和 graph_logic，并检查基础容器结构。"""

    if not isinstance(graph_record, dict):
        raise SplitInputError(f"DAG 第 {graph_index} 项必须是对象")
    graph_batch_id = graph_record.get("batch_id")
    if not isinstance(graph_batch_id, str) or not graph_batch_id:
        raise SplitInputError(f"DAG 第 {graph_index} 项缺少非空字符串 batch_id")

    graph = graph_record.get("graph")
    graph_logic = graph.get("graph_logic") if isinstance(graph, dict) else None
    if not isinstance(graph_logic, dict):
        raise SplitInputError(f"DAG 第 {graph_index} 项缺少 graph.graph_logic 对象")

    conditions = graph_logic.get("conditions")
    intermediate_steps = graph_logic.get("intermediate_steps")
    final_conclusion = graph_logic.get("final_conclusion")
    if not isinstance(conditions, list):
        raise SplitInputError(f"DAG 第 {graph_index} 项的 conditions 必须是数组")
    if not isinstance(intermediate_steps, list):
        raise SplitInputError(f"DAG 第 {graph_index} 项的 intermediate_steps 必须是数组")
    if not isinstance(final_conclusion, dict):
        raise SplitInputError(f"DAG 第 {graph_index} 项的 final_conclusion 必须是对象")
    return graph_batch_id, graph_logic


def collect_graph_nodes(
    graph_logic: dict[str, Any], graph_batch_id: str
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """按 C、I、O 顺序收集节点，检查节点 ID、内容和父节点引用。"""

    raw_nodes = [
        *graph_logic["conditions"],
        *graph_logic["intermediate_steps"],
        graph_logic["final_conclusion"],
    ]
    lookup: dict[str, dict[str, Any]] = {}
    for node_index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise SplitInputError(f"图 {graph_batch_id} 的第 {node_index} 个节点必须是对象")
        node_id = node.get("id")
        content = node.get("content")
        if not isinstance(node_id, str) or not node_id:
            raise SplitInputError(f"图 {graph_batch_id} 的第 {node_index} 个节点缺少非空 id")
        if not isinstance(content, str):
            raise SplitInputError(f"图 {graph_batch_id} 的节点 {node_id} 的 content 必须是字符串")
        if node_id in lookup:
            raise SplitInputError(f"图 {graph_batch_id} 的节点 id 重复：{node_id}")
        lookup[node_id] = node

    for node in [*graph_logic["intermediate_steps"], graph_logic["final_conclusion"]]:
        node_id = node["id"]
        parents = node.get("parents")
        if not isinstance(parents, list):
            raise SplitInputError(f"图 {graph_batch_id} 的节点 {node_id} 的 parents 必须是数组")
        for parent_id in parents:
            if not isinstance(parent_id, str) or parent_id not in lookup:
                raise SplitInputError(
                    f"图 {graph_batch_id} 的节点 {node_id} 引用了不存在的父节点：{parent_id}"
                )
    return raw_nodes, lookup


def build_node_record(
    graph_batch_id: str, node: dict[str, Any], reasoning_chain: str
) -> dict[str, str]:
    """将一个 C/I/O 节点转换为节点 JSON 中的精简记录。"""

    return {
        "batch_id": make_node_batch_id(graph_batch_id, node["id"]),
        "reasoning_chain_model": reasoning_chain,
        "content": node["content"],
    }


def build_relation_record(
    graph_batch_id: str,
    child_node: dict[str, Any],
    lookup: dict[str, dict[str, Any]],
    reasoning_chain: str,
) -> dict[str, Any]:
    """将一个 I/O 子节点及其全部真实父节点转换为一个关系单元。"""

    parent_records = [
        {
            "batch_id": make_node_batch_id(graph_batch_id, parent_id),
            "content": lookup[parent_id]["content"],
        }
        for parent_id in child_node["parents"]
    ]
    return {
        "batch_id": make_node_batch_id(graph_batch_id, child_node["id"]),
        "reasoning_chain_model": reasoning_chain,
        "content": child_node["content"],
        "parents": parent_records,
        "reasoning_logic": child_node.get("reasoning_logic", ""),
        "type": child_node.get("type", ""),
    }


def make_node_batch_id(graph_batch_id: str, node_id: str) -> str:
    """按“图 batch_id-节点 id”规则构造节点或关系记录的 batch_id。"""

    return f"{graph_batch_id}-{node_id}"


def write_json_atomically(path: Path, data: list[dict[str, Any]]) -> None:
    """先写入同目录临时文件，再替换目标文件，避免留下半个 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(path)


def execute(
    dag_input_path: Path,
    cot_input_path: Path,
    nodes_output_path: Path,
    relations_output_path: Path,
) -> int:
    """读取双输入、拆分节点与关系，并写出两个 JSON 文件。"""

    dag_input_path = resolve_project_path(dag_input_path)
    cot_input_path = resolve_project_path(cot_input_path)
    nodes_output_path = resolve_project_path(nodes_output_path)
    relations_output_path = resolve_project_path(relations_output_path)
    validate_distinct_paths(
        [dag_input_path, cot_input_path, nodes_output_path, relations_output_path]
    )

    cot_by_batch_id = load_cot_by_batch_id(cot_input_path)
    dag_records = load_json_array(dag_input_path, "DAG")
    node_records, relation_records = split_dag_records(dag_records, cot_by_batch_id)
    write_json_atomically(nodes_output_path, node_records)
    write_json_atomically(relations_output_path, relation_records)

    print(f"DAG 图数量：{len(dag_records)}")
    print(f"节点数量：{len(node_records)}")
    print(f"关系单元数量：{len(relation_records)}")
    print(f"节点输出：{nodes_output_path}")
    print(f"关系输出：{relations_output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(
            args.dag_input_json,
            args.cot_input_json,
            args.nodes_output_json,
            args.relations_output_json,
        )
    except SplitInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


'''
python scripts/split_dag_nodes_relations.py `
  data\cot-1\llava-cot-11b\dag.json data\cot-1\llava-cot-11b\cot.json `
  data\cot-1\llava-cot-11b\node.json data\cot-1\llava-cot-11b\relationship.json

python scripts/split_dag_nodes_relations.py `
  data\cot-1\gemini-3.1pro\dag.json data\cot-1\gemini-3.1pro\cot.json `
  data\cot-1\gemini-3.1pro\node.json data\cot-1\gemini-3.1pro\relationship.json
'''