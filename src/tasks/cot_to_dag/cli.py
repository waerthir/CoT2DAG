"""CoT 转 DAG 任务的命令行入口。"""

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

from .adapter import DAGTaskAdapter, InputDataError


def build_parser() -> argparse.ArgumentParser:
    """创建并返回 CoT 转 DAG 命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="Asynchronous resumable CoT-to-DAG batch processing")
    parser.add_argument(
        "command", choices=("run", "status", "retry-failed", "export"), help="Command to execute"
    )
    parser.add_argument(
        "--config", type=Path, required=True, help="YAML configuration file"
    )
    return parser


async def execute(command: str, config_path: Path) -> int:
    """按命令名称执行 run、status、retry-failed 或 export，并返回退出码。"""
    config = load_config(config_path)
    # status / retry-failed 只需要 SQLite；run 才会创建模型客户端并检查 API 环境变量。
    repository = await TaskRepository.open(config.paths.database)
    try:
        if command == "status":
            _print_counts(await repository.status_counts())
            return 0

        if command == "retry-failed":
            changed = await repository.retry_failed()
            print(f"Reset {changed} failed task(s) to pending.")
            _print_counts(await repository.status_counts())
            return 0

        adapter = DAGTaskAdapter(config.paths.system_prompt)
        if command == "export":
            count, counts = await export_completed(
                adapter, repository, config.paths.input_json, config.paths.output_json
            )
            print(f"Exported {count} completed task(s) to {config.paths.output_json}.")
            _print_counts(counts)
            return 0

        # 此处才会读取 LLM_API_KEY；只有 run 分支会调用模型。
        client = StructuredLlmClient(config)
        counts = await run_pending_tasks(adapter, repository, client, config)
        _print_counts(counts)
        return 0
    finally:
        await repository.close()


def _print_counts(counts: dict[str, int]) -> None:
    """以统一格式打印三种 SQLite 任务状态的数量。"""
    print(
        "Status: "
        f"pending={counts['pending']}, "
        f"completed={counts['completed']}, "
        f"failed={counts['failed']}"
    )


def main() -> int:
    """解析命令行参数、启动异步入口，并把可预期错误转换为退出码。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    try:
        return asyncio.run(execute(args.command, args.config))
    except (ConfigError, InputDataError, LlmConfigurationError) as exc:
        logging.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())



'''

python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-1\gemini-3.1pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-1\gemini-3.1pro\cot_to_dag.yaml


python -m src.tasks.cot_to_dag.cli export --config data\cot-1\gemini-3.1pro\cot_to_dag.yaml
'''