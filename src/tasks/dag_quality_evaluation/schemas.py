"""DAG 质量评分任务使用的输入与输出 Pydantic 模型。"""

from __future__ import annotations

from typing import Annotated, Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class DAGQualityEvaluationInput(BaseModel):
    """一张待评分 DAG 的原始 CoT 与图结构。"""

    model_config = ConfigDict(extra="forbid")

    batch_id: str = Field(min_length=1)
    reasoning_chain_model: str = Field(min_length=1)
    graph: dict[str, Any]


class ConditionNodeEvaluation(BaseModel):
    """模型对 C 层条件节点给出的质量评分。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    node_id: Annotated[str, Field(min_length=3, pattern=r"^C_.+")]
    Information_Fidelity: float = Field(ge=0, le=10)
    Claim_Atomicity: float = Field(ge=0, le=10)
    Node_Type_Correctness: float = Field(ge=0, le=10)


class ReasoningNodeEvaluation(BaseModel):
    """模型对 I/O 层推理节点给出的质量评分。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    node_id: Annotated[str, Field(min_length=1, pattern=r"^(?:I_.+|O(?:_.+)?)$")]
    Information_Fidelity: float = Field(ge=0, le=10)
    Claim_Atomicity: float = Field(ge=0, le=10)
    Node_Type_Correctness: float = Field(ge=0, le=10)
    Dependency_Completeness: float = Field(ge=0, le=10)
    Dependency_Correctness: float = Field(ge=0, le=10)


QualityNodeEvaluation: TypeAlias = ConditionNodeEvaluation | ReasoningNodeEvaluation


class DAGQualityEvaluationOutput(BaseModel):
    """一张完整 DAG 的逐节点评分与图级信息覆盖评分。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    node_evaluations: list[QualityNodeEvaluation]
    Information_Coverage: float = Field(ge=0, le=10)
