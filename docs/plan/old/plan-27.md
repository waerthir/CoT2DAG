# 图级 DAG 节点评估任务计划

## 新任务包

- 新建与 `cot_to_dag` 平级的 `src/tasks/dag_evaluation/`。
- 新增 `schemas.py`、`adapter.py`、`cli.py` 与 `__init__.py`。
- 复用现有 `src/batch_engine` 的 SQLite 状态管理、动态 worker、Tenacity、模型客户端与导出器。

## 输入与消息构造

- Adapter 读取 `combine.json` 顶层列表，校验每条 `batch_id` 唯一，并读取：`batch_id`、`problem_text`、`ground_truths`、`image_paths`、`graph`。
- `batch_id` 仅作为 SQLite 任务 ID 与最终导出 ID，不发送给模型。
- 用户文本消息只序列化：

  ```json
  {
    "problem_text": "...",
    "ground_truths": ["..."],
    "graph": {"graph_logic": {}}
  }
  ```

- 对每个 `image_paths` 本地文件将相对路径按项目根目录解析，读取二进制内容后按文件 MIME 类型编码为 base64 `image_url` 内容块，附加到同一条用户消息；不把本地文件路径发送给模型。
- 读取不到图片、图片 MIME 类型无法确定或输入字段不合法时，在模型调用前报告对应 `batch_id`。
- 系统提示词由 YAML 指向 `docs/prompt/dag_eval.md`。

## 输出模型与任务校验

- 定义结构化输出：

  ```json
  {
    "node_evaluations": [
      {"node_id": "C_1", "is_correct": true}
    ]
  }
  ```

- 从输入 `graph.graph_logic` 依次提取 `conditions`、`intermediate_steps`、`final_conclusion` 的节点 ID，形成预期节点序列。
- 校验模型输出的 `node_evaluations`：节点数一致、无重复、节点 ID 与预期集合一致、顺序与预期 C → I → O 顺序一致；`is_correct` 必须为布尔值。
- 导出单条结果为：

  ```json
  {
    "batch_id": "<sample_id>",
    "node_evaluations": [
      {"node_id": "C_1", "is_correct": true}
    ]
  }
  ```

## CLI 与配置

- `cli.py` 提供与 `cot_to_dag` 相同的 `run`、`status`、`retry-failed`、`export` 命令。
- 每个模型目录使用独立配置文件 `dag_evaluation.yaml`：

  ```yaml
  paths:
    input_json: data/dag-reasoning-eval-1/<model>/combine.json
    database: data/dag-reasoning-eval-1/<model>/dag_evaluation.sqlite3
    output_json: data/dag-reasoning-eval-1/<model>/dag_evaluation.json
    system_prompt: docs/prompt/dag_eval.md
  ```

- 模型、并发、超时、流式和重试配置沿用现有单模型 YAML 结构。

## 验收

- 对一条含图片的 combine 记录，确认模型消息包含题目、Ground Truth、完整图和实际图片内容。
- 模型漏评、重复评或乱序评节点时，任务不得写入 completed。
- `export` 按 `combine.json` 原始顺序输出已完成图级评估结果。
