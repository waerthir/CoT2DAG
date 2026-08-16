"""将 CoT 与 DAG 构造成 DAG 质量评分批处理任务。"""

from __future__ import annotations

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Literal

from pydantic import TypeAdapter, ValidationError

from .schemas import (
    ConditionNodeEvaluation,
    DAGQualityEvaluationInput,
    DAGQualityEvaluationOutput,
    QualityNodeEvaluation,
    ReasoningNodeEvaluation,
)

NodeLayer = Literal["C", "I", "O"]


class DAGQualityEvaluationInputError(ValueError):
    """DAG 质量评分的输入、提示词或模型输出不符合要求时抛出的异常。"""


class DAGQualityEvaluationTaskAdapter:
    """构造 CoT 与完整 DAG 的质量评分消息，并校验六维评分输出。"""

    output_model = DAGQualityEvaluationOutput

    def __init__(self, system_prompt_path: Path) -> None:
        """读取 DAG 质量评分的系统提示词。"""

        try:
            self._system_prompt = system_prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise DAGQualityEvaluationInputError(
                f"DAG 质量评分提示词文件不存在：{system_prompt_path}"
            ) from exc
        if not self._system_prompt.strip():
            raise DAGQualityEvaluationInputError(
                f"DAG 质量评分提示词文件为空：{system_prompt_path}"
            )
        self._expected_nodes_context: ContextVar[tuple[tuple[str, NodeLayer], ...] | None] = (
            ContextVar("dag_quality_evaluation_expected_nodes", default=None)
        )

    def load_items(self, input_path: Path) -> list[DAGQualityEvaluationInput]:
        """读取抽样 CoT-DAG JSON，并检查任务 ID 与 DAG 节点结构。"""

        try:
            raw_data = json.loads(input_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise DAGQualityEvaluationInputError(f"质量评分输入文件不存在：{input_path}") from exc
        except json.JSONDecodeError as exc:
            raise DAGQualityEvaluationInputError(
                f"质量评分输入文件不是合法 JSON：{exc}"
            ) from exc
        if not isinstance(raw_data, list):
            raise DAGQualityEvaluationInputError("质量评分输入 JSON 顶层必须是列表。")

        try:
            items = TypeAdapter(list[DAGQualityEvaluationInput]).validate_python(raw_data)
        except ValidationError as exc:
            raise DAGQualityEvaluationInputError(f"质量评分输入字段不合法：{exc}") from exc

        batch_ids = [item.batch_id for item in items]
        if len(batch_ids) != len(set(batch_ids)):
            raise DAGQualityEvaluationInputError("质量评分输入中的 batch_id 必须唯一。")
        for item in items:
            _expected_nodes(item.graph, item.batch_id)
        return items

    def get_batch_id(self, item: DAGQualityEvaluationInput) -> str:
        """返回输入记录的 batch_id，供批处理引擎关联任务状态。"""

        return item.batch_id

    def build_messages(self, item: DAGQualityEvaluationInput) -> list[dict[str, Any]]:
        """构造只含原始 CoT 与图结构的系统消息和用户消息。"""

        # 每个 asyncio worker 拥有独立 ContextVar 上下文，避免并发评分任务的
        # 节点层级校验信息相互覆盖。
        self._expected_nodes_context.set(tuple(_expected_nodes(item.graph, item.batch_id)))
        user_data = {
            "reasoning_chain_model": item.reasoning_chain_model,
            "graph": item.graph,
        }
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": json.dumps(user_data, ensure_ascii=False, indent=2)},
        ]

    def validate_output(
        self, output: DAGQualityEvaluationOutput
    ) -> DAGQualityEvaluationOutput:
        """确认节点顺序、C/I/O 指标边界与输出节点集合完全正确。"""

        expected_nodes = self._expected_nodes_context.get()
        if expected_nodes is None:
            raise DAGQualityEvaluationInputError("当前任务缺少用于校验输出的 DAG 节点规格。")

        actual_node_ids = tuple(item.node_id for item in output.node_evaluations)
        expected_node_ids = tuple(node_id for node_id, _ in expected_nodes)
        if actual_node_ids != expected_node_ids:
            raise DAGQualityEvaluationInputError(
                "模型输出的 node_evaluations 必须覆盖全部节点，并保持 C → I → O 顺序。"
            )

        for node_output, (_, layer) in zip(
            output.node_evaluations, expected_nodes, strict=True
        ):
            _validate_node_layer(node_output, layer)
        return output

    def export_record(
        self, batch_id: str, output: DAGQualityEvaluationOutput
    ) -> dict[str, Any]:
        """保留逐节点评分，并计算六项图级质量分数。"""

        node_evaluations = [
            item.model_dump(mode="json", exclude_none=True)
            for item in output.node_evaluations
        ]
        dependency_nodes = [
            item
            for item in output.node_evaluations
            if isinstance(item, ReasoningNodeEvaluation)
        ]
        if not dependency_nodes:
            raise DAGQualityEvaluationInputError(
                "质量评分输出缺少 I/O 节点，无法计算 Dependency 图级平均分。"
            )
        return {
            "batch_id": batch_id,
            "node_evaluations": node_evaluations,
            "dag_evaluation": {
                "Information_Fidelity": _mean_score(
                    output.node_evaluations, "Information_Fidelity"
                ),
                "Claim_Atomicity": _mean_score(
                    output.node_evaluations, "Claim_Atomicity"
                ),
                "Node_Type_Correctness": _mean_score(
                    output.node_evaluations, "Node_Type_Correctness"
                ),
                "Dependency_Completeness": _mean_score(
                    dependency_nodes, "Dependency_Completeness"
                ),
                "Dependency_Correctness": _mean_score(
                    dependency_nodes, "Dependency_Correctness"
                ),
                "Information_Coverage": output.Information_Coverage,
            },
        }


def _expected_nodes(graph: dict[str, Any], batch_id: str) -> list[tuple[str, NodeLayer]]:
    """按 C、I、O 层提取唯一节点 ID，并保留每个节点所属层级。"""

    graph_logic = graph.get("graph_logic")
    if not isinstance(graph_logic, dict):
        raise DAGQualityEvaluationInputError(
            f"batch_id={batch_id} 缺少 graph.graph_logic 对象。"
        )
    conditions = graph_logic.get("conditions")
    intermediate_steps = graph_logic.get("intermediate_steps")
    final_conclusion = graph_logic.get("final_conclusion")
    if not isinstance(conditions, list) or not isinstance(intermediate_steps, list):
        raise DAGQualityEvaluationInputError(
            f"batch_id={batch_id} 的 conditions 和 intermediate_steps 必须是列表。"
        )
    if not isinstance(final_conclusion, dict):
        raise DAGQualityEvaluationInputError(
            f"batch_id={batch_id} 的 final_conclusion 必须是对象。"
        )

    expected_nodes: list[tuple[str, NodeLayer]] = []
    for layer, nodes in (
        ("C", conditions),
        ("I", intermediate_steps),
        ("O", [final_conclusion]),
    ):
        for node in nodes:
            if not isinstance(node, dict):
                raise DAGQualityEvaluationInputError(
                    f"batch_id={batch_id} 存在不是对象的 {layer} 节点。"
                )
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                raise DAGQualityEvaluationInputError(
                    f"batch_id={batch_id} 存在缺少 id 的 {layer} 节点。"
                )
            expected_nodes.append((node_id, layer))
    node_ids = [node_id for node_id, _ in expected_nodes]
    if len(node_ids) != len(set(node_ids)):
        raise DAGQualityEvaluationInputError(f"batch_id={batch_id} 的 DAG 节点 ID 存在重复。")
    return expected_nodes


def _validate_node_layer(
    node_output: QualityNodeEvaluation, layer: NodeLayer
) -> None:
    """按输入 DAG 层级确认节点使用了对应的严格评分 Schema。"""

    if layer == "C":
        if not isinstance(node_output, ConditionNodeEvaluation):
            raise DAGQualityEvaluationInputError(
                f"C 节点 {node_output.node_id} 必须使用 C 节点评分结构。"
            )
        return
    if not isinstance(node_output, ReasoningNodeEvaluation):
        raise DAGQualityEvaluationInputError(
            f"{layer} 节点 {node_output.node_id} 必须使用 I/O 节点评分结构。"
        )


def _mean_score(node_evaluations: list[QualityNodeEvaluation], field_name: str) -> float:
    """计算指定质量分数的算术平均值，并保留两位小数。"""

    values = [getattr(item, field_name) for item in node_evaluations]
    if not values or any(value is None for value in values):
        raise DAGQualityEvaluationInputError(f"无法计算 {field_name} 的图级平均分。")
    return round(sum(values) / len(values), 2)
