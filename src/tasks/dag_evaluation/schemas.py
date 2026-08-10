"""图级 DAG 节点评估任务的输入与输出 Pydantic 模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class DAGEvaluationInput(BaseModel):
    """一张待评估 DAG 图及其题目、Ground Truth 和本地图片信息。"""

    model_config = ConfigDict(extra="allow")

    batch_id: str = Field(min_length=1)
    problem_text: str = Field(min_length=1)
    ground_truths: list[str]
    image_paths: list[str]
    graph: dict[str, Any]


class NodeEvaluationResult(BaseModel):
    """模型对一个 DAG 节点给出的二值正确性判断。"""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1)
    is_correct: StrictBool


class DAGEvaluationOutput(BaseModel):
    """一张完整 DAG 图中全部节点的二值评估结果。"""

    model_config = ConfigDict(extra="forbid")

    node_evaluations: list[NodeEvaluationResult]
