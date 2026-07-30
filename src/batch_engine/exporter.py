"""按输入顺序导出已完成任务的结果。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .db import TaskRepository
from .runner import BatchTaskAdapter, InputT, OutputT


async def export_completed(
    adapter: BatchTaskAdapter[InputT, OutputT],
    repository: TaskRepository,
    input_path: Path,
    output_path: Path,
) -> tuple[int, dict[str, int]]:
    """按当前输入顺序导出全部 completed 任务，并返回导出数和状态统计。"""

    records: list[dict[str, Any]] = []
    # 重新按输入数组顺序遍历，而不是按 SQLite 内部顺序导出。
    for item in adapter.load_items(input_path):
        batch_id = adapter.get_batch_id(item)
        raw_result = await repository.get_completed_result(batch_id)
        if raw_result is None:
            continue
        # 导出前再次按输出 Schema 读取，防止手工改库导致无效 JSON 被导出。
        output = adapter.output_model.model_validate_json(raw_result)
        records.append(adapter.export_record(batch_id, output))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 临时文件写完后再替换目标文件，避免中途停止留下半个 JSON 文件。
    temporary_path.replace(output_path)
    return len(records), await repository.status_counts()
