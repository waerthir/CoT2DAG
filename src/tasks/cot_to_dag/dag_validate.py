"""Pydantic 结构解析完成后的 DAG 业务规则校验。"""

from __future__ import annotations

from .schemas import DAGOutput


def validate_dag(output: DAGOutput) -> DAGOutput:
    """验证 DAG 的节点 ID、父节点引用、自环和整体无环性。"""
    graph = output.graph_logic
    # 先将三层节点合并，统一检查 ID 与父节点引用。
    nodes = [*graph.conditions, *graph.intermediate_steps, graph.final_conclusion]
    node_ids = [node.id for node in nodes]

    if len(node_ids) != len(set(node_ids)):
        raise ValueError("DAG node IDs must be unique")

    available_ids = set(node_ids)
    # dependency_map 的方向是“子节点 -> 父节点”，用于后面的深度优先无环检查。
    dependency_map: dict[str, list[str]] = {}
    for node in [*graph.intermediate_steps, graph.final_conclusion]:
        if node.id in node.parents:
            raise ValueError(f"DAG node {node.id} cannot depend on itself")
        missing_parents = set(node.parents) - available_ids
        if missing_parents:
            raise ValueError(
                f"DAG node {node.id} references missing parents: {sorted(missing_parents)}"
            )
        dependency_map[node.id] = node.parents

    _assert_acyclic(available_ids, dependency_map)
    return output


def _assert_acyclic(node_ids: set[str], dependency_map: dict[str, list[str]]) -> None:
    """使用深度优先遍历检查“节点指向父节点”的依赖关系是否有环。"""

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        """递归访问一个节点及其父节点，用 visiting 集合发现循环依赖。"""
        # 再次访问正在递归路径中的节点，表示出现环。
        if node_id in visiting:
            raise ValueError(f"DAG contains a cycle at node {node_id}")
        if node_id in visited:
            return
        visiting.add(node_id)
        for parent_id in dependency_map.get(node_id, []):
            visit(parent_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        visit(node_id)
