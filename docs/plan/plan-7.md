# 模型请求最小间隔计划

## 改动范围

- 修改 `src/batch_engine/config.py`：为 `ModelConfig` 增加请求间隔配置。
- 修改 `src/batch_engine/llm_client.py`：在 `StructuredLlmClient` 中加入共享异步请求节流器，并在实际模型调用前接入。
- 保持全部已有任务 YAML 原样；配置模型为未来手动添加的 `min_request_interval_s` 提供读取与校验能力。
- 新增本地异步测试，验证节流器、Tenacity 重试顺序和并发 worker 下的请求发起顺序，不发送真实模型请求。

## YAML 配置

- 在 `model` 下增加：

  ```yaml
  model:
    max_concurrency: 4
    min_request_interval_s: 1.0
  ```

- `min_request_interval_s` 的含义是：同一个 `StructuredLlmClient` 实例中，相邻两次真实模型请求的发起许可至少相隔该秒数。
- 配置类型为非负浮点数，默认值为 `0`；字段缺省时立即取得许可。
- Pydantic 在加载 YAML 时拒绝负数和非有限数值。

## 节流器实现

- 在 `llm_client.py` 内定义轻量的异步节流器，保存：
  - 配置的最小间隔；
  - 一个 `asyncio.Lock`；
  - 下一次允许发起请求的单调时钟时间。
- `StructuredLlmClient.__init__` 创建一个节流器实例；同一批任务的全部 worker 共用这一实例。
- 节流器在取得许可时执行以下顺序：

  ```python
  async with pacing_lock:
      now = monotonic_clock()
      wait_s = max(0, next_allowed_at - now)
      if wait_s:
          await asyncio.sleep(wait_s)
      next_allowed_at = monotonic_clock() + min_request_interval_s
  ```

- 节流锁只覆盖“计算等待、异步等待、更新时间点”的短流程；模型网络调用、响应解析和 SQLite 写入均在锁外执行。
- `min_request_interval_s == 0` 时直接返回，不创建额外等待。
- 节流器仅记录发起许可，不记录任务状态、不改变队列顺序，也不引入新的失败状态。

## 与并发 worker 的关系

- 保留 `runner.py` 的共享队列和动态 worker 调度。
- `max_concurrency` 继续限制同一时刻处于模型调用阶段的任务数量。
- 当多个 worker 同时准备发起请求时，节流器按取得锁的顺序依次放行；每个 worker 在取得许可后立即开始自身模型调用。
- 已经取得许可并开始等待模型响应的 worker 不占用节流锁；后续 worker 可在达到最小间隔后开始新的请求。
- 例如 `max_concurrency: 4`、`min_request_interval_s: 1.0` 时，请求按至少一秒的间隔开始，多个尚未返回的请求可以同时在途。

## 与 Tenacity 重试的关系

- 保持现有 Tenacity 的 `retry_predicate`、`max_attempts`、`min_wait_s`、`max_wait_s` 和 Instructor `max_retries=0` 设置。
- 将节流器等待置于 Tenacity 单次尝试的 `with attempt:` 内部，并紧邻 LiteLLM/Instructor 调用之前：

  ```python
  async for attempt in AsyncRetrying(...):
      with attempt:
          await request_pacer.wait_for_turn()
          return await instructor_client.chat.completions.create(...)
  ```

- 首次调用执行“取得节流许可 → 发送请求”。
- 可重试失败后执行“Tenacity 退避等待 → 取得节流许可 → 再次发送请求”。
- Tenacity 的退避时间与全局最小间隔分别生效：前者针对失败任务的再次尝试，后者约束全部 worker 的请求发起频率。
- 单次尝试在本地参数校验或上游调用阶段失败后，仍视为一次已取得的请求许可；后续尝试继续遵守全局间隔。

## 可观测性

- 节流器实际等待时记录 DEBUG 日志，包含本次等待秒数；正常未等待的请求不增加 INFO 日志。
- 现有 LiteLLM 日志、任务完成/失败日志和数据库状态输出保持原有格式。

## 本地验收

- 配置缺省与显式 `min_request_interval_s: 0` 时，节流器不调用 `asyncio.sleep`。
- 配置正数间隔时，连续取得许可的时间差不小于配置值。
- 多个并发协程同时请求许可时，许可时间按全局间隔依次分开；节流锁不会覆盖模拟的模型网络等待。
- 模拟一次可重试失败后，第二次模型调用发生在 Tenacity 退避完成且节流许可取得之后。
- 模拟不可重试失败时，不产生额外尝试。
- YAML 中的负数、`NaN`、`Infinity` 配置在加载阶段报错。
