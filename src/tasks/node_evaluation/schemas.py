"""节点评分任务的输入与输出 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NodeEvaluationInput(BaseModel):
    """一条待评分节点记录的基础字段。"""

    batch_id: str = Field(min_length=1)
    reasoning_chain_model: str = Field(min_length=1)
    content: str = Field(min_length=1)


class NodeEvaluation(BaseModel):
    """节点信息忠实度与原子化程度的评分结果。"""

    Fidelity: float = Field(ge=0, le=10)
    Atomicity: float = Field(ge=0, le=10)
