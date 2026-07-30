# CoT 批量转换 DAG：施工计划

## 1. 目标

读取一个 JSON 数组。每个元素必须携带唯一的字符串 `batch_id`，并可提取一个 CoT（当前字段为 `reasoning_chain_model`）。对每个 CoT 异步调用模型：DAG 规则以 system message 发送，当前 CoT 以 user message 发送。通过校验的 DAG 写入 SQLite，并按当前输入文件顺序导出整体 JSON。

通用能力沉入 Batch Engine：异步并发、模型调用、Tenacity 重试、SQLite 状态保存和导出。DAG Task Adapter 负责本任务的输入、提示词、DAG Schema 和图校验；后续批量 LLM 任务替换 Adapter 即可复用 Engine。

```text
input.json + YAML + docs/prompt/cot_to_dag_system.md
                         |
                         v
    DAG Task Adapter（输入校验、CoT、消息、DAG Schema/图校验）
                         |
                         v
 Batch Engine（Queue worker、LiteLLM、Instructor、Tenacity、SQLite）
                         |
                         v
          tasks 表（batch_id、status、result_json）
                         |
                         v
                  按输入顺序导出 JSON
```

## 2. 模块与目录

```text
src/
  batch_engine/
    config.py             # YAML -> Pydantic 配置
    db.py                 # aiosqlite、简短 SQL、Repository
    runner.py             # asyncio.Queue + 固定 worker
    llm_client.py         # LiteLLM + Instructor 异步调用
    retry.py              # Tenacity 策略与错误分类
    exporter.py           # 读取结果、按输入顺序导出
  tasks/
    cot_to_dag/
      adapter.py          # 输入读取、CoT、提示词读取、消息、导出记录
      schemas.py          # 输入 Schema 与 DAG Pydantic Schema
      dag_validate.py     # DAG 跨节点及无环校验
      cli.py              # run / status / retry-failed / export
configs/
  cot_to_dag.yaml
docs/prompt/
  cot_to_dag_system.md
```

命令入口使用任务命名空间，避免占用通用的 `src.cli`：

```bash
python -m src.tasks.cot_to_dag.cli <command> --config configs/cot_to_dag.yaml
```

## 3. DAG Task Adapter

### 3.1 输入约束

输入模型至少包含：

```python
class InputItem(BaseModel):
    batch_id: str = Field(min_length=1)
    reasoning_chain_model: str = Field(min_length=1)
```

Adapter 在读取输入后检查 `batch_id` 全文件唯一；对被 JSON 字符串包裹的 CoT 做一次安全解码，再生成当前任务的 user message。

### 3.2 Adapter 接口

```python
class BatchTaskAdapter(Protocol[OutputT]):
    output_model: type[BaseModel]

    def load_items(self, input_path: Path) -> list[InputItem]: ...
    def get_batch_id(self, item: InputItem) -> str: ...
    def extract_cot(self, item: InputItem) -> str: ...
    def build_messages(self, cot: str) -> list[dict]: ...
    def validate_output(self, output: OutputT) -> OutputT: ...
    def export_record(self, batch_id: str, output: OutputT) -> dict: ...
```

`adapter.py` 直接读取 YAML 指定的提示词文件：

```python
system_prompt = Path(config.paths.system_prompt).read_text(encoding="utf-8")
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": cot},
]
```

### 3.3 DAG 输出约束

`schemas.py` 定义条件节点、中间推理节点、最终结论及 `DAGOutput` 的 Pydantic Schema。`dag_validate.py` 实现以下校验：

- 节点 ID 唯一；
- `C_*` 节点没有父节点；
- `I_*` 和 `O` 的父节点均存在；
- 无自环、无环；
- `O` 是唯一最终结论；
- 节点类型属于提示词规定的枚举。

## 4. YAML 配置

```yaml
paths:
  input_json: data/input.json
  database: data/cot_to_dag.sqlite3
  output_json: data/cot_to_dag_all.json
  system_prompt: docs/prompt/cot_to_dag_system.md

model:
  litellm_model: openai/gpt-5-mini
  api_base: https://gateway.example/v1
  api_key_env: LLM_API_KEY
  timeout_s: 90
  max_concurrency: 4
  completion_kwargs:
    temperature: 0.1

retry:
  max_attempts: 5
  min_wait_s: 2
  max_wait_s: 60
  retry_invalid_output: true
```

Pydantic 在启动时校验路径、正整数参数和必填字段。中转站地址是 YAML 中的普通连接配置；模型密钥由 YAML 指向的环境变量提供：

```text
LLM_API_KEY=...
```

`max_concurrency` 决定固定 worker 数和同时在飞的模型请求数，是并发控制的主要参数。`timeout_s` 限制单次请求占用 worker 的最长时间；`retry` 段只控制失败任务的重试。实际运行从 4 开始，根据 429、超时和平均响应时间调整为 6 或 8。

`min_wait_s` 是首次重试的退避基准，`max_wait_s` 是单次退避上限；Tenacity 使用指数退避加抖动。`max_attempts` 包含首次调用，设置为 5 时单个任务最多请求 5 次。

## 5. SQLite 状态保存

### 5.1 表结构

数据库首次运行时自动创建，只使用一张 `tasks` 表：

```sql
CREATE TABLE IF NOT EXISTS tasks (
    batch_id    TEXT PRIMARY KEY,
    status      TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    result_json TEXT
);
```

| 字段 | 含义 |
| --- | --- |
| `batch_id` | 输入元素自带的唯一字符串任务标识。 |
| `status` | `pending`、`completed`、`failed`。 |
| `result_json` | `completed` 状态对应的已校验 DAG JSON。 |

### 5.2 状态与初始化

```text
INSERT OR IGNORE -> pending --成功--> completed
                               |
                               +--达到 max_attempts--> failed

retry-failed: failed -------------------------------> pending
```

启动步骤：读取输入、验证 `batch_id`、对每个 `batch_id` 执行 `INSERT OR IGNORE`、查询当前输入中状态为 `pending` 的任务、启动 worker。`completed` 任务跳过。`retry-failed` 执行：

```sql
UPDATE tasks SET status = 'pending' WHERE status = 'failed';
```

SQLite 以提交成功作为完成判据。强制关闭时，已提交的 `completed` 保留；尚未提交终态的任务继续保持 `pending`，下次重新请求。

### 5.3 连接和写入规则

每次 Runner 只创建一个 `aiosqlite.Connection`，所有 worker 共享同一个 Repository。Repository 用一个 `asyncio.Lock` 包住每个短写事务：

```python
class TaskRepository:
    def __init__(self, connection: aiosqlite.Connection):
        self.connection = connection
        self.write_lock = asyncio.Lock()

    async def mark_completed(self, batch_id: str, result: dict) -> None:
        async with self.write_lock:
            await self.connection.execute(
                "UPDATE tasks SET status=?, result_json=? WHERE batch_id=?",
                ("completed", json.dumps(result, ensure_ascii=False), batch_id),
            )
            await self.connection.commit()
```

模型请求和 DAG 校验位于锁外；SQLite 写入按短事务串行。每个数据库文件由一个 Runner 进程使用。

## 6. 异步执行

### 6.1 初始化

```python
async def prepare(adapter, repo, config):
    items = adapter.load_items(config.paths.input_json)
    for item in items:
        await repo.insert_pending_if_missing(adapter.get_batch_id(item))
    return items
```

### 6.2 Queue worker

```python
async def run(adapter, repo, config):
    items = await prepare(adapter, repo, config)
    item_by_id = {adapter.get_batch_id(item): item for item in items}
    pending_ids = await repo.list_pending_ids(item_by_id.keys())

    queue = asyncio.Queue()
    for batch_id in pending_ids:
        queue.put_nowait(batch_id)

    async def process_one(batch_id: str):
        item = item_by_id[batch_id]
        try:
            dag = await call_model_with_retry(
                adapter.build_messages(adapter.extract_cot(item)),
                adapter.output_model,
                config,
            )
            dag = adapter.validate_output(dag)
            await repo.mark_completed(batch_id, dag.model_dump(mode="json"))
        except FinalTaskError:
            await repo.mark_failed(batch_id)

    async def worker():
        while True:
            try:
                batch_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await process_one(batch_id)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker())
               for _ in range(config.model.max_concurrency)]
    await queue.join()
    await asyncio.gather(*workers)
```

worker 完成一个任务后立即领取下一任务；`queue.join()` 等待全部任务执行 `task_done()`，`gather()` 等待 worker 退出。结果在 `process_one` 中立即写 SQLite，不按固定批次汇总。

### 6.3 模型调用、结构化输出与重试

```python
@retry(
    retry=retry_if_exception(is_retryable_error),
    wait=wait_exponential_jitter(
        initial=config.retry.min_wait_s,
        max=config.retry.max_wait_s,
    ),
    stop=stop_after_attempt(config.retry.max_attempts),
    reraise=True,
)
async def call_model_with_retry(messages, output_model, config):
    return await instructor_client.chat.completions.create(
        model=config.model.litellm_model,
        messages=messages,
        response_model=output_model,
        api_base=config.model.api_base,
        api_key=os.environ[config.model.api_key_env],
        max_retries=0,
        **config.model.completion_kwargs,
    )
```

Tenacity 是唯一重试层。`is_retryable_error` 覆盖网络断连、连接/读取超时、429、供应商 5xx，以及配置允许时的结构化输出校验错误。401/403、模型名错误、请求参数错误和上下文超限直接进入 `failed`。

## 7. 导出与命令

Exporter 重新读取当前输入文件，按输入数组顺序遍历 `batch_id`，读取对应 `completed` 结果，调用 `adapter.export_record` 生成最终记录。导出内容建议保留 `batch_id`：

```json
[
  {
    "batch_id": "sample-0001",
    "graph": {"graph_logic": {}}
  }
]
```

```bash
# 初始化、补齐任务并处理 pending
python -m src.tasks.cot_to_dag.cli run --config configs/cot_to_dag.yaml

# 查看 pending / completed / failed 数量
python -m src.tasks.cot_to_dag.cli status --config configs/cot_to_dag.yaml

# 将 failed 重置为 pending
python -m src.tasks.cot_to_dag.cli retry-failed --config configs/cot_to_dag.yaml

# 只导出 completed 结果
python -m src.tasks.cot_to_dag.cli export --config configs/cot_to_dag.yaml
```

## 8. 实施顺序与验收

1. 建立依赖、YAML 配置、Pydantic 配置模型、提示词文件和目录结构。
2. 实现 `DAGTaskAdapter`、输入 `batch_id` 校验、DAG 输出 Schema 与 DAG 图校验。
3. 实现 `aiosqlite` Repository：建表、初始化、查询、完成/失败更新、失败重置和结果读取。
4. 实现 LiteLLM 中转站调用、Instructor 结构化输出和 Tenacity 单一重试策略。
5. 实现 Queue worker、任务 CLI 和有序导出。
6. 用少量样本及 `max_concurrency: 4` 试跑；确认状态恢复、输出 Schema、SQLite 写入和中转站参数后调整并发度。

验收结果：每个当前输入的 `batch_id` 处于 `pending`、`completed` 或 `failed` 之一；成功 DAG 可从 SQLite 有序导出；重启后跳过 `completed` 并继续 `pending`；`retry-failed` 能将失败任务重新加入队列。
