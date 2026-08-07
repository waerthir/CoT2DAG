# 结构化输出兼容性修复计划

- 在 `src/batch_engine/llm_client.py` 的 `StructuredLlmClient.__init__` 中，将 `instructor.from_litellm(acompletion)` 改为显式指定 `instructor.Mode.JSON_SCHEMA`。
- 保留 `create` 内现有的请求参数、流式 `create_partial` 分支、非流式 `create` 分支、Pydantic 最终校验和 Tenacity 重试逻辑。
- 不新增 YAML 配置、模式分支、回退逻辑或特殊重试规则；中转站若不支持 JSON Schema，保持其原始错误输出。
