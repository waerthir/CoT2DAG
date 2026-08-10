"""将 combine.json 转换为图级 DAG 节点评估任务的适配器。"""

from __future__ import annotations

import base64
import json
import mimetypes
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .schemas import DAGEvaluationInput, DAGEvaluationOutput


class DAGEvaluationInputError(ValueError):
    """图级 DAG 评估的输入、图片或系统提示词不合法时抛出的异常。"""


class DAGEvaluationTaskAdapter:
    """构造包含题目、Ground Truth、完整 DAG 与实际图片的模型消息。"""

    output_model = DAGEvaluationOutput

    def __init__(self, system_prompt_path: Path) -> None:
        """读取图级 DAG 节点评估使用的系统提示词。"""

        try:
            self._system_prompt = system_prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise DAGEvaluationInputError(
                f"图级 DAG 评估提示词文件不存在：{system_prompt_path}"
            ) from exc
        if not self._system_prompt.strip():
            raise DAGEvaluationInputError(
                f"图级 DAG 评估提示词文件为空：{system_prompt_path}"
            )
        self._project_root = _find_project_root()
        self._expected_node_ids_context: ContextVar[tuple[str, ...] | None] = ContextVar(
            "dag_evaluation_expected_node_ids", default=None
        )

    def load_items(self, input_path: Path) -> list[DAGEvaluationInput]:
        """读取 combine.json，并检查 batch_id 和 DAG 节点序列。"""

        try:
            raw_data = json.loads(input_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise DAGEvaluationInputError(f"图级评估输入文件不存在：{input_path}") from exc
        except json.JSONDecodeError as exc:
            raise DAGEvaluationInputError(f"图级评估输入文件不是合法 JSON：{exc}") from exc
        if not isinstance(raw_data, list):
            raise DAGEvaluationInputError("图级评估输入 JSON 顶层必须是列表。")

        try:
            items = TypeAdapter(list[DAGEvaluationInput]).validate_python(raw_data)
        except ValidationError as exc:
            raise DAGEvaluationInputError(f"图级评估输入字段不合法：{exc}") from exc

        batch_ids = [item.batch_id for item in items]
        if len(batch_ids) != len(set(batch_ids)):
            raise DAGEvaluationInputError("图级评估输入中的 batch_id 必须唯一。")
        for item in items:
            _expected_node_ids(item.graph, item.batch_id)
        return items

    def get_batch_id(self, item: DAGEvaluationInput) -> str:
        """返回 combine 记录中的 sample_id 作为内部任务 ID。"""

        return item.batch_id

    def build_messages(self, item: DAGEvaluationInput) -> list[dict[str, Any]]:
        """构造系统提示词、文本评估材料和实际图片组成的多模态消息。"""

        # 每个 asyncio worker 都有独立 ContextVar 上下文，供随后 validate_output
        # 校验同一条任务的模型输出，不会在并发任务之间串扰。
        self._expected_node_ids_context.set(tuple(_expected_node_ids(item.graph, item.batch_id)))
        user_data = {
            "problem_text": item.problem_text,
            "ground_truths": item.ground_truths,
            "graph": item.graph,
        }
        content_blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": json.dumps(user_data, ensure_ascii=False, indent=2),
            }
        ]
        for image_path in item.image_paths:
            content_blocks.append(self._build_image_block(image_path, item.batch_id))

        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": content_blocks},
        ]

    def validate_output(self, output: DAGEvaluationOutput) -> DAGEvaluationOutput:
        """确认模型恰好按 C、I、O 顺序评估输入图中的全部节点。"""

        expected_node_ids = self._expected_node_ids_context.get()
        if expected_node_ids is None:
            raise DAGEvaluationInputError("当前任务缺少用于校验模型输出的 DAG 节点序列。")
        actual_node_ids = [item.node_id for item in output.node_evaluations]
        if tuple(actual_node_ids) != expected_node_ids:
            raise DAGEvaluationInputError(
                "模型输出的 node_evaluations 必须覆盖全部节点，并保持 C → I → O 顺序。"
            )
        return output

    def export_record(self, batch_id: str, output: DAGEvaluationOutput) -> dict[str, Any]:
        """将一张图的节点二值评估结果包装为最终导出记录。"""

        return {"batch_id": batch_id, **output.model_dump(mode="json")}

    def _build_image_block(self, image_path_text: str, batch_id: str) -> dict[str, Any]:
        """读取本地图片并转换为 OpenAI 兼容的 base64 image_url 内容块。"""

        image_path = Path(image_path_text)
        if not image_path.is_absolute():
            image_path = self._project_root / image_path
        try:
            image_bytes = image_path.read_bytes()
        except FileNotFoundError as exc:
            raise DAGEvaluationInputError(
                f"batch_id={batch_id} 的图片文件不存在：{image_path}"
            ) from exc
        if not image_bytes:
            raise DAGEvaluationInputError(f"batch_id={batch_id} 的图片文件为空：{image_path}")

        mime_type, _ = mimetypes.guess_type(image_path.name)
        if not mime_type or not mime_type.startswith("image/"):
            raise DAGEvaluationInputError(
                f"batch_id={batch_id} 的图片 MIME 类型无法确定：{image_path}"
            )
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"},
        }


def _expected_node_ids(graph: dict[str, Any], batch_id: str) -> list[str]:
    """从 graph_logic 按 conditions、intermediate_steps、final_conclusion 提取节点顺序。"""

    graph_logic = graph.get("graph_logic")
    if not isinstance(graph_logic, dict):
        raise DAGEvaluationInputError(f"batch_id={batch_id} 缺少 graph.graph_logic 对象。")

    conditions = graph_logic.get("conditions")
    intermediate_steps = graph_logic.get("intermediate_steps")
    final_conclusion = graph_logic.get("final_conclusion")
    if not isinstance(conditions, list) or not isinstance(intermediate_steps, list):
        raise DAGEvaluationInputError(
            f"batch_id={batch_id} 的 conditions 和 intermediate_steps 必须是列表。"
        )
    if not isinstance(final_conclusion, dict):
        raise DAGEvaluationInputError(
            f"batch_id={batch_id} 的 final_conclusion 必须是对象。"
        )

    ordered_nodes = [*conditions, *intermediate_steps, final_conclusion]
    node_ids: list[str] = []
    for node in ordered_nodes:
        if not isinstance(node, dict):
            raise DAGEvaluationInputError(f"batch_id={batch_id} 存在不是对象的 DAG 节点。")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise DAGEvaluationInputError(f"batch_id={batch_id} 存在缺少 id 的 DAG 节点。")
        node_ids.append(node_id)
    if len(node_ids) != len(set(node_ids)):
        raise DAGEvaluationInputError(f"batch_id={batch_id} 的 DAG 节点 ID 存在重复。")
    return node_ids


def _find_project_root() -> Path:
    """从当前任务模块向上查找带 pyproject.toml 的项目根目录。"""

    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()
