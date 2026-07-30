"""关系评分任务的 BatchTaskAdapter 实现。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .schemas import RelationshipEvaluation, RelationshipEvaluationInput


class RelationshipEvaluationInputError(ValueError):
    """关系评分输入文件或提示词文件不合法时抛出的异常。"""


class RelationshipEvaluationTaskAdapter:
    """将关系记录转换为评分模型请求，并导出评分结果。"""

    output_model = RelationshipEvaluation

    def __init__(self, system_prompt_path: Path) -> None:
        """读取关系评分任务使用的系统提示词。"""

        try:
            self._system_prompt = system_prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RelationshipEvaluationInputError(
                f"关系评分提示词文件不存在：{system_prompt_path}"
            ) from exc
        if not self._system_prompt.strip():
            raise RelationshipEvaluationInputError(f"关系评分提示词文件为空：{system_prompt_path}")

    def load_items(self, input_path: Path) -> list[RelationshipEvaluationInput]:
        """读取关系 JSON 数组并检查必需字段和 parents 容器。"""

        try:
            raw_data = json.loads(input_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RelationshipEvaluationInputError(f"关系输入文件不存在：{input_path}") from exc
        except json.JSONDecodeError as exc:
            raise RelationshipEvaluationInputError(f"关系输入文件不是合法 JSON：{exc}") from exc
        if not isinstance(raw_data, list):
            raise RelationshipEvaluationInputError("关系输入 JSON 顶层必须是数组")
        try:
            items = TypeAdapter(list[RelationshipEvaluationInput]).validate_python(raw_data)
        except ValidationError as exc:
            raise RelationshipEvaluationInputError(f"关系输入字段不合法：{exc}") from exc
        _ensure_unique_batch_ids(items)
        return items

    def get_batch_id(self, item: RelationshipEvaluationInput) -> str:
        """返回关系记录的 batch_id。"""

        return item.batch_id

    def build_messages(self, item: RelationshipEvaluationInput) -> list[dict[str, Any]]:
        """构造包含 CoT、父节点和推理字段的评分消息。"""

        user_data = {
            "reasoning_chain_model": item.reasoning_chain_model,
            "content": item.content,
            "parents": [parent.model_dump(mode="json") for parent in item.parents],
            "reasoning_logic": item.reasoning_logic,
            "type": item.type,
        }
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": json.dumps(user_data, ensure_ascii=False, indent=2)},
        ]

    def validate_output(self, output: RelationshipEvaluation) -> RelationshipEvaluation:
        """直接返回已经由 Pydantic 校验过范围的评分结果。"""

        return output

    def export_record(self, batch_id: str, output: RelationshipEvaluation) -> dict[str, Any]:
        """将关系评分结果包装为导出记录。"""

        return {"batch_id": batch_id, "evaluation": output.model_dump(mode="json")}


def _ensure_unique_batch_ids(items: list[RelationshipEvaluationInput]) -> None:
    """检查输入内 batch_id 唯一，避免多个任务写入同一 SQLite 记录。"""

    batch_ids = [item.batch_id for item in items]
    if len(batch_ids) != len(set(batch_ids)):
        raise RelationshipEvaluationInputError("关系输入中的 batch_id 必须唯一")
