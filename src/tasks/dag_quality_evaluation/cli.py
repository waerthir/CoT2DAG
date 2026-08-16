"""DAG 质量评分任务的命令行入口。"""

from __future__ import annotations

import ssl

ssl.SSLContext._load_windows_store_certs = lambda self, storename, purpose: None

import argparse
import asyncio
import logging
from pathlib import Path

from src.batch_engine.config import ConfigError, load_config
from src.batch_engine.db import TaskRepository
from src.batch_engine.exporter import export_completed
from src.batch_engine.llm_client import LlmConfigurationError, StructuredLlmClient
from src.batch_engine.runner import run_pending_tasks

from .adapter import DAGQualityEvaluationInputError, DAGQualityEvaluationTaskAdapter


def build_parser() -> argparse.ArgumentParser:
    """创建 DAG 质量评分任务的命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="可恢复的异步 DAG 质量评分任务")
    parser.add_argument("command", choices=("run", "status", "retry-failed", "export"))
    parser.add_argument("--config", type=Path, required=True, help="YAML 配置文件路径")
    return parser


async def execute(command: str, config_path: Path) -> int:
    """执行 run、status、retry-failed 或 export 命令。"""

    config = load_config(config_path)
    repository = await TaskRepository.open(config.paths.database)
    try:
        if command == "status":
            _print_counts(await repository.status_counts())
            return 0
        if command == "retry-failed":
            changed = await repository.retry_failed()
            print(f"已将 {changed} 条 DAG 质量评分任务重置为 pending。")
            _print_counts(await repository.status_counts())
            return 0

        adapter = DAGQualityEvaluationTaskAdapter(config.paths.system_prompt)
        if command == "export":
            count, counts = await export_completed(
                adapter, repository, config.paths.input_json, config.paths.output_json
            )
            print(f"已导出 {count} 条 DAG 质量评分结果：{config.paths.output_json}")
            _print_counts(counts)
            return 0

        client = StructuredLlmClient(config)
        _print_counts(await run_pending_tasks(adapter, repository, client, config))
        return 0
    finally:
        await repository.close()


def _print_counts(counts: dict[str, int]) -> None:
    """打印 pending、completed 与 failed 三种任务状态数量。"""

    print(
        f"状态：pending={counts['pending']}，"
        f"completed={counts['completed']}，"
        f"failed={counts['failed']}"
    )


def main() -> int:
    """解析参数、运行异步命令，并转换可预期的输入错误。"""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    try:
        return asyncio.run(execute(args.command, args.config))
    except (ConfigError, DAGQualityEvaluationInputError, LlmConfigurationError) as exc:
        logging.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logging.warning("用户中断任务。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
