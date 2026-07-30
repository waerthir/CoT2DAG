"""CoT 输入与 DAG 结构化输出所使用的 Pydantic 模型。"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class InputItem(BaseModel):
    """一个原始输入元素；允许存在本任务未使用的额外字段。"""

    # 原始数据可能携带问题、答案等额外字段；本任务只要求下面两个字段。
    model_config = ConfigDict(extra="allow")

    batch_id: str = Field(min_length=1)
    reasoning_chain_model: str = Field(min_length=1)


# 用正则限制节点 ID，避免模型生成 C_0、condition_1 等不统一格式。
ConditionId = Annotated[str, Field(pattern=r"^C_[1-9][0-9]*$")]
IntermediateId = Annotated[str, Field(pattern=r"^I_[1-9][0-9]*$")]


class ConditionNode(BaseModel):
    id: ConditionId
    type: Literal["文字信息", "图像信息", "学科常识"]
    content: str = Field(min_length=1)


class ReasoningNode(BaseModel):
    id: IntermediateId
    type: Literal["条件转化", "逻辑推导", "数值计算", "对比分析", "综合归纳"]
    content: str = Field(min_length=1)
    parents: list[str] = Field(min_length=1)
    reasoning_logic: str = Field(min_length=1)


class FinalConclusion(BaseModel):
    id: Literal["O"]
    type: Literal["条件转化", "逻辑推导", "数值计算", "对比分析", "综合归纳"]
    content: str = Field(min_length=1)
    parents: list[str] = Field(min_length=1)
    reasoning_logic: str = Field(min_length=1)


class GraphLogic(BaseModel):
    conditions: list[ConditionNode]
    intermediate_steps: list[ReasoningNode]
    final_conclusion: FinalConclusion


class DAGOutput(BaseModel):
    graph_logic: GraphLogic
