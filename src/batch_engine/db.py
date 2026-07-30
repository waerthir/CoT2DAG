"""用于断点续传批处理任务的最小 SQLite 仓储层。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from pathlib import Path

import aiosqlite


class TaskRepository:
    """共享单个连接的任务仓储；写操作按顺序执行。"""

    def __init__(self, connection: aiosqlite.Connection) -> None:
        """保存共享数据库连接，并创建保护短写事务的异步锁。"""
        # 所有 worker 共用一个连接，避免每个 worker 单独连接 SQLite 后相互抢写锁。
        self._connection = connection
        # 锁只包住很短的写入和 commit；模型网络请求不在锁内，仍然保持并发。
        self._write_lock = asyncio.Lock()

    @classmethod
    async def open(cls, database_path: Path) -> "TaskRepository":
        """创建数据库父目录、打开 SQLite 连接并确保 tasks 表存在。"""
        # data/ 等父目录可能首次运行时不存在，先创建目录再打开数据库文件。
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(database_path)
        repository = cls(connection)
        await repository.create_table_if_missing()
        return repository

    async def close(self) -> None:
        """关闭本次 Runner 使用的 SQLite 连接。"""
        await self._connection.close()

    async def create_table_if_missing(self) -> None:
        """首次运行时创建保存任务状态和 DAG 结果的最小 tasks 表。"""
        async with self._write_lock:
            await self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    batch_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
                    result_json TEXT
                )
                """
            )
            await self._connection.commit()

    async def insert_pending_if_missing(self, batch_id: str) -> None:
        """为新 batch_id 插入 pending；已有记录的状态和结果保持不变。"""
        async with self._write_lock:
            # 旧任务已经存在时保持原状态；新 batch_id 才会进入 pending。
            await self._connection.execute(
                "INSERT OR IGNORE INTO tasks (batch_id, status) VALUES (?, 'pending')",
                (batch_id,),
            )
            await self._connection.commit()

    async def list_pending_ids(self, allowed_ids: Iterable[str]) -> list[str]:
        """返回当前输入集合中状态为 pending 的 batch_id 列表。"""
        # 只查询当前输入文件里的 ID，数据库中的历史 ID 不进入本轮队列。
        allowed = list(allowed_ids)
        if not allowed:
            return []
        placeholders = ", ".join("?" for _ in allowed)
        query = (
            "SELECT batch_id FROM tasks "
            f"WHERE status = 'pending' AND batch_id IN ({placeholders})"
        )
        async with self._connection.execute(query, allowed) as cursor:
            return [row[0] async for row in cursor]

    async def mark_completed(self, batch_id: str, result: dict[str, object]) -> None:
        """将校验通过的 DAG JSON 保存，并把对应任务标记为 completed。"""
        # 只有 Pydantic 与 DAG 校验均通过后，Runner 才调用本方法。
        result_json = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        async with self._write_lock:
            await self._connection.execute(
                "UPDATE tasks SET status = 'completed', result_json = ? WHERE batch_id = ?",
                (result_json, batch_id),
            )
            await self._connection.commit()

    async def mark_failed(self, batch_id: str) -> None:
        """将达到重试上限或不可恢复的任务标记为 failed。"""
        async with self._write_lock:
            await self._connection.execute(
                "UPDATE tasks SET status = 'failed' WHERE batch_id = ?",
                (batch_id,),
            )
            await self._connection.commit()

    async def retry_failed(self) -> int:
        """将全部 failed 任务重置为 pending，并返回本次重置数量。"""
        async with self._write_lock:
            # 用户显式执行 retry-failed 后，所有失败任务回到可领取状态。
            cursor = await self._connection.execute(
                "UPDATE tasks SET status = 'pending' WHERE status = 'failed'"
            )
            await self._connection.commit()
            return cursor.rowcount

    async def get_completed_result(self, batch_id: str) -> str | None:
        """读取一个 completed 任务的原始 DAG JSON；没有结果时返回 None。"""
        async with self._connection.execute(
            "SELECT result_json FROM tasks WHERE batch_id = ? AND status = 'completed'",
            (batch_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return None if row is None else row[0]

    async def status_counts(self) -> dict[str, int]:
        """统计 pending、completed、failed 三种状态的任务数量。"""
        counts = {"pending": 0, "completed": 0, "failed": 0}
        async with self._connection.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status"
        ) as cursor:
            async for status, count in cursor:
                counts[status] = count
        return counts
