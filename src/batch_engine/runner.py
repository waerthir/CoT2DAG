"""基于队列的动态异步批处理执行逻辑。"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .config import AppConfig
from .db import TaskRepository
from .llm_client import FinalTaskError, StructuredLlmClient

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT", bound=BaseModel)
logger = logging.getLogger(__name__)


class BatchTaskAdapter(Protocol[InputT, OutputT]):
    """任务适配器约定：Batch Engine 通过这些方法处理不同业务任务。"""

    output_model: type[OutputT]

    def load_items(self, input_path: Path) -> list[InputT]:
        """读取并校验某一任务类型的全部输入元素。"""
        ...

    def get_batch_id(self, item: InputT) -> str:
        """返回输入元素用于数据库状态映射的唯一 batch_id。"""
        ...

    def build_messages(self, item: InputT) -> list[dict[str, Any]]:
        """从原始输入元素构造本次发送给模型的消息列表。"""
        ...

    def validate_output(self, output: OutputT) -> OutputT:
        """执行任务专属的业务校验，并返回已确认可保存的输出。"""
        ...

    def export_record(self, batch_id: str, output: OutputT) -> dict[str, Any]:
        """将一个已完成输出转换为最终导出文件中的记录。"""
        ...


async def run_pending_tasks(
    adapter: BatchTaskAdapter[InputT, OutputT],
    repository: TaskRepository,
    client: StructuredLlmClient,
    config: AppConfig,
) -> dict[str, int]:
    """登记当前输入任务，并用动态 worker 并发处理全部 pending 任务。"""

    items = adapter.load_items(config.paths.input_json)
    # 建立 batch_id -> 原始元素映射；后续数据库只保存 batch_id，不保存原始输入内容。
    item_by_id = {adapter.get_batch_id(item): item for item in items}
    for batch_id in item_by_id:
        # INSERT OR IGNORE 使重复运行同一输入文件时不会覆盖完成结果。
        await repository.insert_pending_if_missing(batch_id)

    pending_ids = await repository.list_pending_ids(item_by_id)
    queue: asyncio.Queue[str] = asyncio.Queue()
    for batch_id in pending_ids:
        queue.put_nowait(batch_id)

    async def process_one(batch_id: str) -> None:
        """处理一个任务：调用模型、校验 DAG，并更新 completed 或 failed 状态。"""
        item = item_by_id[batch_id]
        try:
            # 模型请求在 SQLite 写锁外执行；多个 worker 可同时等待模型响应。
            response = await client.create(adapter.build_messages(item), adapter.output_model)
            output = adapter.validate_output(response)
            # 一条任务完成后立刻提交，而不是等整批任务结束后再统一保存。
            await repository.mark_completed(batch_id, output.model_dump(mode="json"))
            logger.info("Completed batch_id=%s", batch_id)
        except (FinalTaskError, ValueError) as exc:
            await repository.mark_failed(batch_id)
            logger.warning("Failed batch_id=%s: %s", batch_id, exc)

    async def worker(worker_index: int) -> None:
        """持续从共享队列取任务；完成一条后立即领取下一条。"""
        while True:
            try:
                # 任一 worker 做完当前任务后立即领取下一条，属于动态调度。
                batch_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_one(batch_id)
            finally:
                queue.task_done()

    worker_count = min(config.model.max_concurrency, queue.qsize())
    # worker 数量就是同时在飞的模型请求上限；队列为空时创建零个 worker。
    workers = [asyncio.create_task(worker(index)) for index in range(worker_count)]
    # join 等待所有 queue.task_done()；gather 只负责等待 worker 自然退出，不会分批处理任务。
    await queue.join()
    await asyncio.gather(*workers)
    return await repository.status_counts()
