# 模型请求最小间隔计划

## 配置

- 在 `model` 配置中新增可选字段 `min_request_interval_s`。
- 字段类型为非负浮点数；YAML 未填写时默认 `0`，保持现有请求行为。
- 需要限制请求频率时，在对应任务 YAML 的 `model` 下填写秒数，例如：

  ```yaml
  model:
    max_concurrency: 4
    min_request_interval_s: 1.0
  ```

## 请求节流

- 在 `StructuredLlmClient` 内创建一个由该客户端共享的异步请求节流器。
- 当 `min_request_interval_s > 0` 时，所有 worker 在每次实际发起模型请求前先取得节流器许可。
- 使用异步锁与单调时钟，保证相邻两次请求开始时间至少间隔配置的秒数。
- 节流器只控制请求的发起时刻；已发出的请求继续并行等待响应，`max_concurrency` 继续控制在途请求上限。
- Tenacity 的每次重试在真正调用模型前同样经过节流器。

## 接入位置

- 扩展 `src/batch_engine/config.py` 的 `ModelConfig`，读取并校验该可选字段。
- 在 `src/batch_engine/llm_client.py` 中，将节流等待放在 Tenacity 单次尝试内部、LiteLLM/Instructor 调用之前。
- 不改变队列 worker、SQLite 状态写入、任务适配器和已有重试参数的职责。

## 验收

- 未配置 `min_request_interval_s` 时，任务运行不增加请求等待。
- 配置正数间隔且 `max_concurrency > 1` 时，多个 worker 的模型请求开始时间满足全局最小间隔，同时已在途请求可以重叠。
- 自动重试产生的请求同样满足最小间隔。
- 负数配置在加载 YAML 时被拒绝。
