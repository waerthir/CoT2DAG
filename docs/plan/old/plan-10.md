# 结构化模型调用的流式配置计划

- 采用独立的 `model.stream` 设置入口，不通过 `completion_kwargs` 管理流式传输。
- 在 `src/batch_engine/config.py` 的 `ModelConfig` 增加布尔字段 `stream`，默认 `false`；全部已有 YAML 保持原样并使用非流式调用。
- 将 `model.stream` 作为流式开关的唯一配置来源；加载 YAML 时拒绝 `completion_kwargs` 中的 `stream` 参数。

## 客户端调用分支

- 在 `src/batch_engine/llm_client.py` 的 `StructuredLlmClient.create` 保留 Tenacity 循环和请求间隔许可。
- 在当前 `with attempt:` 内、`await self._request_pacer.wait_for_turn()` 后直接构造本次调用的共同参数，并按 `model.stream` 分支：

  ```python
  await self._request_pacer.wait_for_turn()
  request_kwargs = {...}
  if self._config.model.stream:
      last_partial = None
      async for partial in self._client.chat.completions.create_partial(**request_kwargs):
          last_partial = partial
      if last_partial is None:
          raise ValueError("流式响应没有返回结构化结果")
      return output_model.model_validate(last_partial.model_dump())
  return await self._client.chat.completions.create(**request_kwargs)
  ```

- `request_kwargs` 在 `create` 的单次尝试内构造，供两个分支共同使用，包含模型、消息、认证、超时、结构化响应模型和普通透传参数。
- 流式分支和非流式分支均在现有 `create` 内返回最终 `BaseModel`。Tenacity、请求节流、`FinalTaskError` 包装和数据库状态逻辑继续集中在现有 `create` 与 `runner.py`。

## 流式分支处理

- 使用当前环境 `Instructor 1.15.4` 的 `self._client.chat.completions.create_partial(...)` 建立结构化异步流。
- 将现有 `request_kwargs` 传给 `create_partial`，不自行传入 `stream=True`；Instructor 负责设置底层 LiteLLM 流式参数，并将原始流解析为 `Partial[output_model]` 结构化片段。
- 在 `create` 的 `if self._config.model.stream:` 分支内，`async for` 消费 Instructor 返回的结构化片段，保存最后一个片段，检查最终片段存在，并通过 `output_model.model_validate(...)` 将其严格校验回原始输出模型。
- 不在项目内实现 token 拼接、原始 JSON 拼接、SSE 事件解析或自定义流式 Schema 解析。
- `stream: true` 的请求参数由 `create` 内的 `request_kwargs` 提供；流式分支位于已有 Tenacity、请求节流和 `FinalTaskError` 包装范围内。

## 结构校验职责

- 非流式分支继续将 `response_model=output_model` 传给 Instructor，并直接取得完整 `output_model`。
- 流式 `create_partial(...)` 为允许字段逐步生成，返回 `Partial[output_model]` 片段；最后一次片段仍需要转换为原始的严格 `output_model`。
- 流式分支中的 `output_model.model_validate(last_partial.model_dump())` 仅执行该技术性类型恢复与必填字段检查，使流式和非流式分支向外返回相同类型。
- 任务 Adapter 的 `validate_output` 继续执行任务专属业务校验；流式客户端不加入 DAG、节点或关系评分的业务规则。
- `create_partial(...)` 只建立一次模型流；`async for` 在该流持续到达新结构化片段时逐个异步取得片段，`last_partial = partial` 将当前最新片段覆盖为候选最终结果。

## 流式响应处理

- 流式函数取得异步片段迭代器后，持续消费至迭代结束。
- 每个片段仅在客户端内临时保存，用于更新当前的结构化输出状态。
- 迭代结束后取得最终完整输出，并统一转换或校验为本次任务的 `output_model`。
- 未取得最终输出、最终输出缺少必填字段或无法通过 Pydantic 校验时，抛出本次尝试的异常。
- 只有最终完整且校验通过的 `output_model` 从 `StructuredLlmClient.create` 返回给 `runner.py`。

## 重试与状态边界

- 建立流、消费片段、接收结束事件和最终 Pydantic 校验均放入同一个 Tenacity `with attempt:` 范围。
- 流式过程出现网络异常、超时、迭代异常或最终结构校验异常时，交由现有 `retry_predicate` 判断是否重试。
- 每一次流式尝试在建立流之前继续经过已有 `min_request_interval_s` 请求间隔控制。
- `runner.py` 继续只接收最终输出或 `FinalTaskError`：最终输出写入 completed，耗尽或不可重试错误写入 failed。

## 模块影响边界

- `config.py` 负责读取 `model.stream` 并检查 `completion_kwargs.stream` 冲突。
- `llm_client.py` 负责选择传输模式、消费流式片段、构造最终结构化输出和抛出尝试异常。
- `runner.py`、任务 Adapter、SQLite 表结构、导出格式和已有 YAML 的接口保持不变。

## 本地验收

- 伪造非流式客户端，验证 `stream: false` 保持现有调用与返回结果。
- 伪造异步流，验证流式分支消费全部片段并只返回最终完整模型。
- 伪造缺少最终结果、流中异常和最终校验失败，验证其进入现有 Tenacity 重试路径。
- 验证流式重试的每次建流前均经过请求间隔控制。
- 验证默认 `stream: false` 与 `completion_kwargs.stream` 冲突配置的加载结果。
