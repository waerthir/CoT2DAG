# 节点与关系评分 Adapter：实施计划

## 目标

新增两个基于 `BatchTaskAdapter` 的评分任务：

```text
node.json         -> 节点评分结果 JSON
relationship.json -> 关系评分结果 JSON
```

两个任务复用现有 `src/batch_engine` 的 SQLite 状态、Queue worker、LiteLLM、Instructor、Tenacity 和导出流程；`src/batch_engine` 不作任何修改。

## 任务目录

```text
src/tasks/
  node_evaluation/
    __init__.py
    schemas.py
    adapter.py
    cli.py
  relationship_evaluation/
    __init__.py
    schemas.py
    adapter.py
    cli.py
docs/prompt/
  node_evaluation_system.md
  relationship_evaluation_system.md
```

两个任务包与 `src/tasks/cot_to_dag` 平级，分别参照其 Adapter、Schema、CLI 结构实现。

## 节点评分任务

### 输入

```json
{
  "batch_id": "001-C_1",
  "reasoning_chain_model": "完整 CoT",
  "content": "节点内容"
}
```

### 模型消息

节点 Adapter 将以下字段序列化为 user message：

```json
{
  "reasoning_chain_model": "完整 CoT",
  "content": "节点内容"
}
```

`docs/prompt/node_evaluation_system.md` 迁移 `ref/other_src/dag_comparer_1.py` 中 `SYSTEM_INSTRUCTION` 的正文；将“所有分数为 0 到 10 的整数”调整为“所有分数为 0 到 10 的数，允许小数”，其余评分规则、示例和输出字段保持原样。

### 结构化输出与导出

```python
class NodeEvaluation(BaseModel):
    Fidelity: float = Field(ge=0, le=10)
    Atomicity: float = Field(ge=0, le=10)
```

导出记录：

```json
{
  "batch_id": "001-C_1",
  "evaluation": {
    "Fidelity": 10,
    "Atomicity": 10
  }
}
```

## 关系评分任务

### 输入

```json
{
  "batch_id": "001-I_2",
  "reasoning_chain_model": "完整 CoT",
  "content": "子节点内容",
  "parents": [{"batch_id": "001-C_1", "content": "父节点内容"}],
  "reasoning_logic": "推理逻辑",
  "type": "逻辑推导"
}
```

### 模型消息

关系 Adapter 将以下字段序列化为 user message：

```json
{
  "reasoning_chain_model": "完整 CoT",
  "content": "子节点内容",
  "parents": [{"batch_id": "001-C_1", "content": "父节点内容"}],
  "reasoning_logic": "推理逻辑",
  "type": "逻辑推导"
}
```

`docs/prompt/relationship_evaluation_system.md` 直接迁移 `ref/other_src/dag_comparer_2.py` 中 `SYSTEM_INSTRUCTION` 的正文；仅移除 Python 三引号包裹，不改写评分规则、示例和输出字段。

### 结构化输出与导出

```python
class RelationshipEvaluation(BaseModel):
    Dependency_Completeness: float = Field(ge=0, le=10)
    Dependency_Accuracy: float = Field(ge=0, le=10)
    Reasoning_Logic_Accuracy: float = Field(ge=0, le=10)
    Reasoning_Type_Accuracy: float = Field(ge=0, le=10)
```

导出记录：

```json
{
  "batch_id": "001-I_2",
  "evaluation": {
    "Dependency_Completeness": 10,
    "Dependency_Accuracy": 10,
    "Reasoning_Logic_Accuracy": 10,
    "Reasoning_Type_Accuracy": 10
  }
}
```

## 配置与命令

每份 CoT 数据目录自行保存配置：

```text
data/cot-1/llava-cot-11b/
  node.yaml
  relationship.yaml
```

`node.yaml`：

```yaml
paths:
  input_json: data/cot-1/llava-cot-11b/node.json
  database: data/cot-1/llava-cot-11b/node_evaluation.sqlite3
  output_json: data/cot-1/llava-cot-11b/node_evaluation.json
  system_prompt: docs/prompt/node_evaluation_system.md
```

`relationship.yaml`：

```yaml
paths:
  input_json: data/cot-1/llava-cot-11b/relationship.json
  database: data/cot-1/llava-cot-11b/relationship_evaluation.sqlite3
  output_json: data/cot-1/llava-cot-11b/relationship_evaluation.json
  system_prompt: docs/prompt/relationship_evaluation_system.md
```

两份 YAML 的 `model`、`retry` 段复制同目录 `cot_to_dag.yaml`，按运行需求调整模型参数。

命令入口分别为：

```bash
python -m src.tasks.node_evaluation.cli run --config data/cot-1/llava-cot-11b/node.yaml
python -m src.tasks.relationship_evaluation.cli run --config data/cot-1/llava-cot-11b/relationship.yaml
```

两个 CLI 均提供 `run`、`status`、`retry-failed`、`export`，实现方式参照当前 `cot_to_dag.cli`。

## 实施顺序

1. 创建两份评分 system prompt，原封迁移旧脚本的 `SYSTEM_INSTRUCTION` 正文。
2. 创建两个任务包的 Pydantic 输入/输出 Schema；输入仅校验必需字段的基本类型和容器结构，输出校验评分字段为 0–10 的 `float`。
3. 实现两个 Adapter：读取 JSON、使用 `batch_id`、构造 user message、返回评分 Schema、导出 `{batch_id, evaluation}`。`validate_output` 直接返回 Pydantic 已解析的输出。
4. 创建两个 CLI，接入 `TaskRepository`、`StructuredLlmClient`、`run_pending_tasks`、`export_completed`。
5. 在 `data/cot-1/llava-cot-11b/` 创建 `node.yaml` 和 `relationship.yaml`。
6. 离线检查模块语法、配置字段、输入 Schema 与输出 Schema；真实评分由后续显式运行触发。

不创建 `dag_validate.py`、`validate_*.py` 或其他任务专用业务校验模块。
