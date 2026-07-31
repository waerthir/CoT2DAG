"""LiteLLM 与 Instructor 的模型调用集成。"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import instructor
from litellm import acompletion
from pydantic import BaseModel
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential_jitter

from .config import AppConfig
from .retry import retry_predicate


logger = logging.getLogger(__name__)


class LlmConfigurationError(RuntimeError):
    """发起请求前发现中转站所需配置缺失时抛出的异常。"""


class FinalTaskError(RuntimeError):
    """单个模型任务不可重试或耗尽重试次数后抛出的最终异常。"""


class _RequestPacer:
    """为一个模型客户端的全部请求提供共享的最小发起间隔。"""

    def __init__(self, min_interval_s: float) -> None:
        """保存最小间隔，并初始化保护许可时间的异步锁。"""

        self._min_interval_s = min_interval_s
        self._lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    async def wait_for_turn(self) -> None:
        """等待到全局允许发起下一次模型请求的时刻。"""

        if self._min_interval_s == 0:
            return

        async with self._lock:
            now = time.monotonic()
            wait_s = max(0.0, self._next_allowed_at - now)
            if wait_s > 0:
                logger.debug("模型请求节流等待 %.3f 秒。", wait_s)
                await asyncio.sleep(wait_s)
            self._next_allowed_at = time.monotonic() + self._min_interval_s


class StructuredLlmClient:
    """使用 Instructor 生成结构化输出，并由 Tenacity 统一重试的客户端。"""

    def __init__(self, config: AppConfig) -> None:
        """读取模型 YAML 配置和 API Key 环境变量，并初始化 Instructor 异步客户端。"""
        self._config = config
        # 基础 URL 是普通连接配置，直接从 YAML 读取；密钥才从 .env 读取。
        self._api_key = _required_environment(config.model.api_key_env)
        self._client = instructor.from_litellm(acompletion)
        # 全部 worker 共用同一客户端，因此也共用同一个请求发起节流器。
        self._request_pacer = _RequestPacer(config.model.min_request_interval_s)

    async def create(self, messages: list[dict[str, str]], output_model: type[BaseModel]) -> BaseModel:
        """调用中转站模型并返回符合 output_model 的结构化结果；失败时统一重试。"""
        try:
            async for attempt in AsyncRetrying(
                # Instructor 的 max_retries 固定为 0；这里是全项目唯一的重试入口。
                retry=retry_predicate(self._config.retry.retry_invalid_output),
                wait=wait_exponential_jitter(
                    initial=self._config.retry.min_wait_s,
                    max=self._config.retry.max_wait_s,
                ),
                stop=stop_after_attempt(self._config.retry.max_attempts),
                reraise=True,
            ):
                with attempt:
                    # 每次真实调用（包括 Tenacity 的重试）都先遵守全局发起间隔。
                    await self._request_pacer.wait_for_turn()
                    request_kwargs: dict[str, Any] = {
                        "model": self._config.model.litellm_model,
                        "messages": messages,
                        "response_model": output_model,
                        # URL 来自 YAML；Bearer Key 只来自 .env。
                        "api_base": self._config.model.api_base,
                        "api_key": self._api_key,
                        "timeout": self._config.model.timeout_s,
                        "max_retries": 0,
                        **self._config.model.completion_kwargs,
                    }
                    if self._config.model.stream:
                        last_partial: BaseModel | None = None
                        async for partial in self._client.chat.completions.create_partial(
                            **request_kwargs
                        ):
                            last_partial = partial
                        if last_partial is None:
                            raise ValueError("流式响应没有返回结构化结果")
                        return output_model.model_validate(last_partial.model_dump())
                    return await self._client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            raise FinalTaskError(str(exc)) from exc

        raise FinalTaskError("Retry loop finished without a model response")


def _required_environment(name: str) -> str:
    """读取必填环境变量；变量不存在或为空时抛出配置错误。"""
    # 在真正开始 run 前尽早报出缺失配置，不把空密钥发送给中转站。
    value = os.getenv(name)
    if not value:
        raise LlmConfigurationError(f"Required environment variable is missing: {name}")
    return value
