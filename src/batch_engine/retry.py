"""Batch Engine 共用的重试错误分类逻辑。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from pydantic import ValidationError
from tenacity import retry_if_exception


def retry_predicate(retry_invalid_output: bool) -> Callable[[BaseException], bool]:
    """根据 YAML 配置生成 Tenacity 的统一重试判断函数。"""

    def should_retry(error: BaseException) -> bool:
        """判断一次异常是否属于网络、限流、服务端或可配置的格式错误。"""
        # 输出 Schema 校验失败是否重试，由 YAML 的 retry_invalid_output 决定。
        if isinstance(error, ValidationError):
            return retry_invalid_output
        # 网络故障通常是临时故障，交给 Tenacity 指数退避后再次尝试。
        if isinstance(error, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
            return True

        # LiteLLM/供应商异常通常会带 status_code。429 和 5xx 可以重试。
        status_code = getattr(error, "status_code", None)
        if status_code in {408, 409, 425, 429}:
            return True
        if isinstance(status_code, int) and 500 <= status_code <= 599:
            return True

        name = type(error).__name__.lower()
        if retry_invalid_output and ("validation" in name or "instructor" in name):
            return True
        return False

    return retry_if_exception(should_retry)
