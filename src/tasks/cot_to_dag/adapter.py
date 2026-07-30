"""将原始 CoT 转换为 DAG 任务所使用的适配器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .dag_validate import validate_dag
from .schemas import DAGOutput, InputItem


class InputDataError(ValueError):
    """输入 JSON 无法构成合法任务批次时抛出的异常。"""


class DAGTaskAdapter:
    output_model = DAGOutput

    def __init__(self, system_prompt_path: Path) -> None:
        """读取并保存 DAG 任务的系统提示词文本。"""
        try:
            # 提示词属于 DAG 任务本身，由 YAML 指向 docs/prompt 中的文件。
            self._system_prompt = system_prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise InputDataError(f"System prompt file does not exist: {system_prompt_path}") from exc
        if not self._system_prompt.strip():
            raise InputDataError(f"System prompt file is empty: {system_prompt_path}")

    def load_items(self, input_path: Path) -> list[InputItem]:
        """读取输入 JSON 数组、校验字段，并检查 batch_id 是否唯一。"""
        try:
            # 输入顶层必须是 JSON 数组；Pydantic 在后面逐元素检查字段。
            raw_data = json.loads(input_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise InputDataError(f"Input JSON file does not exist: {input_path}") from exc
        except json.JSONDecodeError as exc:
            raise InputDataError(f"Input JSON is invalid: {exc}") from exc

        if not isinstance(raw_data, list):
            raise InputDataError("Input JSON root must be an array")
        try:
            items = TypeAdapter(list[InputItem]).validate_python(raw_data)
        except ValidationError as exc:
            raise InputDataError(f"Input item validation failed: {exc}") from exc

        # batch_id 是 SQLite 主键，重复值会让两个输入元素写到同一任务，因此必须提前拒绝。
        batch_ids = [item.batch_id for item in items]
        if len(batch_ids) != len(set(batch_ids)):
            raise InputDataError("Input batch_id values must be unique")
        return items

    def get_batch_id(self, item: InputItem) -> str:
        """返回输入元素提供的字符串 batch_id。"""
        return item.batch_id

    def build_messages(self, item: InputItem) -> list[dict[str, Any]]:
        """从输入元素提取 CoT，并构造 system prompt 加用户消息。"""
        cot = item.reasoning_chain_model
        # 兼容旧数据中把整个 CoT 再包一层 JSON 引号的情况，例如 '"第一步\\n第二步"'。
        if cot.startswith('"') and cot.endswith('"'):
            try:
                decoded = json.loads(cot)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, str):
                cot = decoded
        # DAG 规则固定放 system role；每个子任务变化的 CoT 放 user role。
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": cot},
        ]

    def validate_output(self, output: DAGOutput) -> DAGOutput:
        """执行节点引用、节点 ID 和无环等 DAG 业务校验。"""
        return validate_dag(output)

    def export_record(self, batch_id: str, output: DAGOutput) -> dict[str, Any]:
        """将一个 DAG 输出包装为带 batch_id 的导出记录。"""
        return {"batch_id": batch_id, "graph": output.model_dump(mode="json")}
