# Adapter 公共接口去 CoT 化：一次性改造计划

`plan.md` 记录已完成阶段的历史计划，本次及后续改造不修改、不回填、不同步该文件。`plan-2.md` 只用于列出本次实施内容；代码实施完成后无需将任一计划文件作为持续维护的规格。

## 目标

将 Batch Engine 与“CoT”这一具体输入概念解耦。通用执行器只向 Adapter 传递原始输入元素，并获取可直接发送给模型的 `messages`。

改造后的职责：

```text
Batch Engine：item -> Adapter.build_messages(item) -> LLM -> 校验/保存
DAGTaskAdapter：从 item 读取 reasoning_chain_model、解码、构造 DAG 消息
```

## 修改范围

### 1. `src/batch_engine/runner.py`

修改 `BatchTaskAdapter` 协议：

```python
# 修改前
def extract_cot(self, item: InputT) -> str: ...
def build_messages(self, cot: str) -> list[dict[str, str]]: ...

# 修改后
def build_messages(self, item: InputT) -> list[dict[str, Any]]: ...
```

修改 `process_one`：

```python
# 修改前
messages = adapter.build_messages(adapter.extract_cot(item))

# 修改后
messages = adapter.build_messages(item)
```

`list[dict[str, Any]]` 允许后续任务构造纯文本消息或 LiteLLM 支持的多模态内容块；Batch Engine 不解释消息内容。

### 2. `src/tasks/cot_to_dag/adapter.py`

删除公开方法：

```python
extract_cot(self, item: InputItem)
```

将其逻辑直接收进：

```python
def build_messages(self, item: InputItem) -> list[dict[str, Any]]:
    cot = item.reasoning_chain_model
    if cot.startswith('"') and cot.endswith('"'):
        # 尝试 JSON 解码；失败时保留原文本
        ...
    return [
        {"role": "system", "content": self._system_prompt},
        {"role": "user", "content": cot},
    ]
```

这里的 CoT 字段读取和兼容解码属于 `DAGTaskAdapter` 的内部实现；通用协议和 Batch Engine 均不再出现 `cot` 或 `extract_cot`。

### 3. 类型与注释同步

- 更新 `build_messages` 的参数、返回类型和中文 docstring；
- 将 Runner 中“提取 CoT”的解释替换为“Adapter 从原始输入构造消息”；

## 不变部分

以下模块和行为保持不变：

- `batch_id`、SQLite 三态、断点续传；
- Queue worker、并发数、SQLite 写锁；
- LiteLLM、Instructor、Tenacity 调用链；
- DAG 的 Pydantic Schema、图校验和导出格式；
- YAML、`.env`、中转站 URL 与 API Key 配置方式。

## 验收标准

1. `BatchTaskAdapter` 协议中不存在 `extract_cot`；
2. `runner.py` 不含 `extract_cot` 或 CoT 字段名；
3. `DAGTaskAdapter.build_messages` 直接接收 `InputItem`；
4. 对同一输入，构造出的 system/user messages 与改造前语义一致；
5. 不改变任何模型调用、数据库写入或状态转换逻辑。

## 后续评估

后续 DAG 质量评估的输入、输出和执行耦合方式暂不纳入本次改造；待评价任务的具体数据形式与目标明确后，再独立定义对应 Adapter 和执行链路。
