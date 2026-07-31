"""请求最小间隔与重试顺序的本地异步测试。"""

from __future__ import annotations

import asyncio
import sys
import time
import types
import unittest
from typing import Any

from pydantic import BaseModel, ValidationError

# 测试只验证本项目的节流与重试编排，不加载会产生网络或证书副作用的真实 SDK。
fake_instructor = types.ModuleType("instructor")
fake_instructor.from_litellm = lambda _: None
fake_litellm = types.ModuleType("litellm")
fake_litellm.acompletion = object()
sys.modules["instructor"] = fake_instructor
sys.modules["litellm"] = fake_litellm

from src.batch_engine.config import AppConfig, ModelConfig
from src.batch_engine.llm_client import FinalTaskError, StructuredLlmClient, _RequestPacer


class _Output(BaseModel):
    """供伪造模型客户端返回的最小结构化输出。"""

    value: int


class _PartialOutput(BaseModel):
    """模拟 Instructor 流式接口返回的允许字段暂时缺失的结构化片段。"""

    value: int | None = None


class _FakeCompletions:
    """记录调用时间，并按预设结果返回或抛出异常的伪造模型接口。"""

    def __init__(
        self,
        outcomes: list[BaseModel | BaseException] | None = None,
        partial_outcomes: list[list[BaseModel | BaseException]] | None = None,
    ) -> None:
        """保存普通调用和流式调用的预设结果。"""

        self._outcomes = outcomes or []
        self._partial_outcomes = partial_outcomes or []
        self.call_times: list[float] = []
        self.partial_call_times: list[float] = []

    async def create(self, **_: Any) -> BaseModel:
        """记录调用时间，并返回或抛出当前预设结果。"""

        self.call_times.append(time.monotonic())
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def create_partial(self, **_: Any):
        """返回按预设片段逐步产出的异步生成器。"""

        self.partial_call_times.append(time.monotonic())
        outcomes = self._partial_outcomes.pop(0)

        async def stream_partials():
            """依次产生结构化片段，或在指定片段位置抛出异常。"""

            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    raise outcome
                yield outcome

        return stream_partials()


class _FakeInstructorClient:
    """提供与 StructuredLlmClient 所需属性层级相同的伪造客户端。"""

    def __init__(self, completions: _FakeCompletions) -> None:
        """将伪造 completions 暴露为 chat.completions。"""

        self.chat = type("FakeChat", (), {"completions": completions})()


def _build_config(
    max_attempts: int = 1,
    min_interval_s: float = 0.0,
    stream: bool = False,
) -> AppConfig:
    """创建仅用于本地测试的最小批处理配置。"""

    return AppConfig.model_validate(
        {
            "paths": {
                "input_json": "input.json",
                "database": "tasks.sqlite3",
                "output_json": "output.json",
                "system_prompt": "prompt.md",
            },
            "model": {
                "litellm_model": "openai/test-model",
                "api_base": "https://example.invalid/v1",
                "api_key_env": "TEST_API_KEY",
                "timeout_s": 1,
                "max_concurrency": 4,
                "min_request_interval_s": min_interval_s,
                "stream": stream,
            },
            "retry": {
                "max_attempts": max_attempts,
                "min_wait_s": 0.01,
                "max_wait_s": 0.01,
                "retry_invalid_output": True,
            },
        }
    )


def _build_client(config: AppConfig, completions: _FakeCompletions) -> StructuredLlmClient:
    """绕过真实初始化，构造只使用伪造模型接口的客户端。"""

    client = StructuredLlmClient.__new__(StructuredLlmClient)
    client._config = config
    client._api_key = "test-key"
    client._client = _FakeInstructorClient(completions)
    client._request_pacer = _RequestPacer(config.model.min_request_interval_s)
    return client


class RequestPacerTests(unittest.IsolatedAsyncioTestCase):
    """验证请求节流器在本地事件循环中的许可行为。"""

    async def test_zero_interval_returns_without_waiting(self) -> None:
        """间隔为零时连续取得许可不产生额外延迟。"""

        pacer = _RequestPacer(0)
        started_at = time.monotonic()
        await pacer.wait_for_turn()
        await pacer.wait_for_turn()
        self.assertLess(time.monotonic() - started_at, 0.02)

    async def test_concurrent_turns_follow_global_interval(self) -> None:
        """并发协程取得许可的时间按全局最小间隔依次分开。"""

        interval_s = 0.05
        pacer = _RequestPacer(interval_s)
        turn_times: list[float] = []

        async def take_turn() -> None:
            """取得许可后记录当前单调时间。"""

            await pacer.wait_for_turn()
            turn_times.append(time.monotonic())

        await asyncio.gather(*(take_turn() for _ in range(3)))
        turn_times.sort()
        self.assertEqual(len(turn_times), 3)
        self.assertGreaterEqual(turn_times[1] - turn_times[0], interval_s - 0.01)
        self.assertGreaterEqual(turn_times[2] - turn_times[1], interval_s - 0.01)

    async def test_retry_waits_then_obeys_request_interval(self) -> None:
        """可重试失败后的下一次调用同时经过退避和请求节流。"""

        interval_s = 0.03
        config = _build_config(max_attempts=2, min_interval_s=interval_s)
        completions = _FakeCompletions([ConnectionError("temporary"), _Output(value=1)])
        client = _build_client(config, completions)

        response = await client.create([], _Output)

        self.assertEqual(response, _Output(value=1))
        self.assertEqual(len(completions.call_times), 2)
        self.assertGreaterEqual(
            completions.call_times[1] - completions.call_times[0], interval_s - 0.01
        )

    async def test_non_retryable_failure_makes_only_one_call(self) -> None:
        """不可重试异常不会触发额外模型调用。"""

        config = _build_config(max_attempts=3, min_interval_s=0.01)
        completions = _FakeCompletions([ValueError("invalid request")])
        client = _build_client(config, completions)

        with self.assertRaises(FinalTaskError):
            await client.create([], _Output)
        self.assertEqual(len(completions.call_times), 1)

    async def test_streaming_returns_the_last_strict_output(self) -> None:
        """流式分支消费全部片段，并仅返回最后一个完整结果。"""

        config = _build_config(stream=True)
        completions = _FakeCompletions(
            partial_outcomes=[[_PartialOutput(value=1), _PartialOutput(value=2)]]
        )
        client = _build_client(config, completions)

        response = await client.create([], _Output)

        self.assertEqual(response, _Output(value=2))
        self.assertEqual(len(completions.call_times), 0)
        self.assertEqual(len(completions.partial_call_times), 1)

    async def test_streaming_retries_after_stream_error(self) -> None:
        """流中连接异常进入 Tenacity，并在下一次建流前遵守请求间隔。"""

        interval_s = 0.03
        config = _build_config(max_attempts=2, min_interval_s=interval_s, stream=True)
        completions = _FakeCompletions(
            partial_outcomes=[
                [ConnectionError("temporary")],
                [_PartialOutput(value=2)],
            ]
        )
        client = _build_client(config, completions)

        response = await client.create([], _Output)

        self.assertEqual(response, _Output(value=2))
        self.assertEqual(len(completions.partial_call_times), 2)
        self.assertGreaterEqual(
            completions.partial_call_times[1] - completions.partial_call_times[0],
            interval_s - 0.01,
        )

    async def test_streaming_retries_after_final_validation_failure(self) -> None:
        """最后片段不完整时，严格输出校验失败可进入现有重试流程。"""

        config = _build_config(max_attempts=2, stream=True)
        completions = _FakeCompletions(
            partial_outcomes=[
                [_PartialOutput()],
                [_PartialOutput(value=3)],
            ]
        )
        client = _build_client(config, completions)

        response = await client.create([], _Output)

        self.assertEqual(response, _Output(value=3))
        self.assertEqual(len(completions.partial_call_times), 2)


class ModelConfigTests(unittest.TestCase):
    """验证请求最小间隔配置的默认值和非法值处理。"""

    def test_interval_and_stream_default_values(self) -> None:
        """缺省请求间隔和流式开关时使用零秒与非流式模式。"""

        config = ModelConfig(
            litellm_model="openai/test-model",
            api_base="https://example.invalid/v1",
            api_key_env="TEST_API_KEY",
            timeout_s=1,
            max_concurrency=1,
        )
        self.assertEqual(config.min_request_interval_s, 0)
        self.assertFalse(config.stream)

    def test_rejects_negative_and_non_finite_intervals(self) -> None:
        """负数、NaN 和 Infinity 请求间隔在配置创建时被拒绝。"""

        common = {
            "litellm_model": "openai/test-model",
            "api_base": "https://example.invalid/v1",
            "api_key_env": "TEST_API_KEY",
            "timeout_s": 1,
            "max_concurrency": 1,
        }
        for invalid_value in (-1, float("nan"), float("inf")):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaises(ValidationError):
                    ModelConfig(**common, min_request_interval_s=invalid_value)

    def test_rejects_stream_in_completion_kwargs(self) -> None:
        """拒绝在普通透传参数中重复配置流式开关。"""

        with self.assertRaises(ValidationError):
            ModelConfig(
                litellm_model="openai/test-model",
                api_base="https://example.invalid/v1",
                api_key_env="TEST_API_KEY",
                timeout_s=1,
                max_concurrency=1,
                completion_kwargs={"stream": True},
            )
