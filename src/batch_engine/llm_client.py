"""LiteLLM 与 Instructor 的模型调用集成。"""

from __future__ import annotations

import os
from typing import Any

import instructor
from litellm import acompletion
from pydantic import BaseModel
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential_jitter

from .config import AppConfig
from .retry import retry_predicate


class LlmConfigurationError(RuntimeError):
    """发起请求前发现中转站所需配置缺失时抛出的异常。"""


class FinalTaskError(RuntimeError):
    """单个模型任务不可重试或耗尽重试次数后抛出的最终异常。"""


class StructuredLlmClient:
    """使用 Instructor 生成结构化输出，并由 Tenacity 统一重试的客户端。"""

    def __init__(self, config: AppConfig) -> None:
        """读取模型 YAML 配置和 API Key 环境变量，并初始化 Instructor 异步客户端。"""
        self._config = config
        # 基础 URL 是普通连接配置，直接从 YAML 读取；密钥才从 .env 读取。
        self._api_key = _required_environment(config.model.api_key_env)
        self._client = instructor.from_litellm(acompletion)

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
                    return await self._client.chat.completions.create(
                        model=self._config.model.litellm_model,
                        messages=messages,
                        response_model=output_model,
                        # URL 来自 YAML；Bearer Key 只来自 .env。
                        api_base=self._config.model.api_base,
                        api_key=self._api_key,
                        timeout=self._config.model.timeout_s,
                        max_retries=0,
                        **self._config.model.completion_kwargs,
                    )
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
