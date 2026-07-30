"""关系评分任务的输入与输出 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParentNode(BaseModel):
    """关系评分输入中使用的父节点基础信息。"""

    batch_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class RelationshipEvaluationInput(BaseModel):
    """一条待评分关系记录的基础字段。"""

    batch_id: str = Field(min_length=1)
    reasoning_chain_model: str = Field(min_length=1)
    content: str = Field(min_length=1)
    parents: list[ParentNode]
    reasoning_logic: str = Field(min_length=1)
    type: str = Field(min_length=1)


class RelationshipEvaluation(BaseModel):
    """依赖、推理逻辑和推理类型的评分结果。"""

    Dependency_Completeness: float = Field(ge=0, le=10)
    Dependency_Accuracy: float = Field(ge=0, le=10)
    Reasoning_Logic_Accuracy: float = Field(ge=0, le=10)
    Reasoning_Type_Accuracy: float = Field(ge=0, le=10)
