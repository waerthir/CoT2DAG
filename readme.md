# CoT2DAG

本项目用于把一批 Chain of Thought（CoT）转换为结构化 DAG，并对每张 DAG 中的节点进行图级正确性评估。批量调用、异步并发、重试、SQLite 断点续传和导出由统一的批处理引擎提供；不同工作只需提供对应的任务适配器与 YAML 配置。

## 运行准备

在项目根目录安装依赖，并在根目录 `.env` 中配置模型密钥。YAML 内的 `model.api_key_env` 决定要读取哪个环境变量；例如：

```dotenv
CODEX_2_API_API_KEY=你的中转站密钥
```

所有示例均假定命令从项目根目录运行。Windows PowerShell 的换行续写符为反引号 `` ` ``；不换行时可以把一整条命令写在同一行。

## 常用数据链路

```text
原始题目 JSON
  ├─ scripts/extract_problem_id_reasoning_chains.py
  │    └─ cot.json（batch_id + reasoning_chain_model）
  ├─ src.tasks.cot_to_dag
  │    └─ dag.json（每条 CoT 对应一张 DAG）
  ├─ scripts/build_dag_combine.py
  │    └─ combine.json（DAG + 题目 + Ground Truth + 图片本地路径）
  └─ src.tasks.dag_evaluation
       └─ dag_evaluation.json（每张图中各节点的正确/错误判断）
```

`src/batch_engine` 是上述两个任务模块共用的基础组件，通常不直接作为命令行入口运行。

## `scripts/extract_problem_id_reasoning_chains.py`

文件：[scripts/extract_problem_id_reasoning_chains.py](scripts/extract_problem_id_reasoning_chains.py)

这个脚本把原始 JSON 列表中的 `problem_id` 与 `reasoning_chain_model` 提取出来，并将 `problem_id` 重命名为 `batch_id`。它适合把包含大量原始字段的模型输出整理为 CoT→DAG 任务所需的轻量输入。

### 输入示例

输入必须是 JSON 列表；单个元素可带有其他字段，脚本只读取以下两个字段：

```json
[
  {
    "problem_id": "biology/example:open_001",
    "question": "Which stage is shown?",
    "reasoning_chain_model": "The diagram shows ..."
  }
]
```

### 输出示例

输出保持原列表顺序：

```json
[
  {
    "batch_id": "biology/example:open_001",
    "reasoning_chain_model": "The diagram shows ..."
  }
]
```

### 命令行接口

```powershell
python scripts\extract_problem_id_reasoning_chains.py `
  <输入原始JSON路径> `
  <输出cot.json路径>
```

例如：

```powershell
python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\gemini-3.1-pro\gemini-3.1-pro-process1.json `
  data\cot-2\gemini-3.1-pro\cot.json
```

脚本要求输入顶层为列表、每一项为对象，并要求每一项的 `problem_id`、`reasoning_chain_model` 都是字符串。输出路径不能与输入路径相同。

## `src.tasks.cot_to_dag`

目录：[src/tasks/cot_to_dag](src/tasks/cot_to_dag)

该任务把 `cot.json` 中的每条 `reasoning_chain_model` 发送给模型，并以 YAML 所指定的系统提示词约束模型返回 DAG。其适配器读取 `batch_id` 与 CoT，模型输出经过 DAG 结构校验后保存；导出时会恢复为输入中的原始顺序。

### 输入文件示例：`cot.json`

```json
[
  {
    "batch_id": "biology/example:open_001",
    "reasoning_chain_model": "First identify the pupa stage, then ..."
  }
]
```

### 导出文件示例：`dag.json`

```json
[
  {
    "batch_id": "biology/example:open_001",
    "graph": {
      "graph_logic": {
        "conditions": [
          {"id": "C_1", "type": "文字信息", "content": "..."}
        ],
        "intermediate_steps": [
          {
            "id": "I_1",
            "type": "逻辑推导",
            "content": "...",
            "parents": ["C_1"],
            "reasoning_logic": "..."
          }
        ],
        "final_conclusion": {
          "id": "O",
          "type": "综合归纳",
          "content": "...",
          "parents": ["I_1"],
          "reasoning_logic": "..."
        }
      }
    }
  }
]
```

### YAML 接口

每个数据/模型目录使用一份独立 YAML，例如 `data/cot-4/gemma-4-12b-it/cot_to_dag.yaml`：

```yaml
paths:
  input_json: data/cot-4/gemma-4-12b-it/cot.json
  database: data/cot-4/gemma-4-12b-it/dag.sqlite3
  output_json: data/cot-4/gemma-4-12b-it/dag.json
  system_prompt: docs/prompt/cot_to_dag_system.md

model:
  litellm_model: openai/模型名
  api_base: https://你的中转站/v1
  api_key_env: CODEX_2_API_API_KEY
  timeout_s: 45
  max_concurrency: 10
  completion_kwargs:
    temperature: 0.1
  min_request_interval_s: 0.0
  stream: false

retry:
  max_attempts: 3
  min_wait_s: 2
  max_wait_s: 60
  retry_invalid_output: true
```

`paths` 指定输入、SQLite 任务库、导出文件和系统提示词；`model` 指定 LiteLLM 模型、中转站 URL、密钥环境变量、并发、请求间隔和流式模式；`retry` 指定由 Tenacity 统一管理的重试次数与等待范围。

### 命令行接口

四个命令均使用同一份 YAML：

```powershell
# 读取输入，登记 pending 任务，并处理所有未完成任务
python -m src.tasks.cot_to_dag.cli run --config <cot_to_dag.yaml路径>

# 查看 SQLite 中 pending / completed / failed 数量
python -m src.tasks.cot_to_dag.cli status --config <cot_to_dag.yaml路径>

# 将所有 failed 任务重新设为 pending
python -m src.tasks.cot_to_dag.cli retry-failed --config <cot_to_dag.yaml路径>

# 按 cot.json 原顺序导出全部 completed 任务
python -m src.tasks.cot_to_dag.cli export --config <cot_to_dag.yaml路径>
```

例如：

```powershell
python -m src.tasks.cot_to_dag.cli run `
  --config data\cot-4\gemma-4-12b-it\cot_to_dag.yaml
```

## `scripts/build_dag_combine.py`

文件：[scripts/build_dag_combine.py](scripts/build_dag_combine.py)

这个脚本用于把已导出的 `dag.json` 与该模型对应的原始题目 JSON 合并成图级评估所需的 `combine.json`。具体地，它对每张 DAG 做以下整理：

1. 将 DAG 与源题目记录对齐。
2. 从源记录取出 `sample_id`，并把它写为输出的 `batch_id`。
3. 从源记录取出 `question`，写为输出的 `problem_text`。
4. 读取源记录的 `item_path` 所指向的本地题目资源，从 `ready3_open_rewrite.claim_split.claims[*].claim` 提取 Ground Truth，写为 `ground_truths`。
5. 读取 `image_paths`；若该字段为空或不存在，则使用 `image_path`。远程图片路径会按照脚本内预设映射，改写为 `data/download/ready/...` 下的本地路径。
6. 保留 DAG 的 `graph` 内容，最终将题目、Ground Truth、图片与完整图结构写到一条 `combine.json` 记录中。

脚本不会下载图片或 Ground Truth 文件。运行前，需要保证对应资源已经按预设本地目录存在；缺少资源、字段或无法对齐的记录时，脚本会停止并报告原因。

### 两种对齐模式

- `--id-mode problem-id`：将每条 DAG 的原 `batch_id` 视为源 JSON 的 `problem_id`，按值匹配。适用于源 JSON 的 `problem_id` 唯一、且 DAG 是由该 ID 生成的情况。
- `--id-mode source-order`：按数组顺序一一配对。要求 `dag.json` 与源 JSON 条目数相同，且顺序已确认一致。

无论使用哪一种模式，输出 `combine.json` 的 `batch_id` 都来自源记录的 `sample_id`，并要求其唯一。

### 输入与输出示例

`dag.json` 的简化记录：

```json
[
  {
    "batch_id": "biology/example:open_001",
    "graph": {"graph_logic": {}}
  }
]
```

源题目 JSON 的简化记录：

```json
[
  {
    "problem_id": "biology/example:open_001",
    "sample_id": "biology/example:sample_001",
    "question": "Which stage is shown?",
    "image_paths": ["/home/lijingyue/qiujianbo/ready/biology/example.png"],
    "item_path": "/home/lijingyue/LiangEnRui/items/biology/example.json"
  }
]
```

生成的 `combine.json`：

```json
[
  {
    "batch_id": "biology/example:sample_001",
    "problem_text": "Which stage is shown?",
    "ground_truths": ["The expected fact extracted from claims."],
    "image_paths": ["data\\download\\ready\\biology\\example.png"],
    "graph": {"graph_logic": {}}
  }
]
```

### 命令行接口

```powershell
python scripts\build_dag_combine.py `
  <dag.json路径> `
  <源题目JSON路径> `
  <输出combine.json路径> `
  --id-mode <problem-id或source-order>
```

常用的 `problem-id` 示例：

```powershell
python scripts\build_dag_combine.py `
  data\dag-reasoning-eval-1\vl-rethinker-72b\dag.json `
  data\dag-reasoning-eval-1\vl-rethinker-72b\vl-rethinker-72b-process1_translated.json `
  data\dag-reasoning-eval-1\vl-rethinker-72b\combine.json `
  --id-mode problem-id
```

## `src.tasks.dag_evaluation`

目录：[src/tasks/dag_evaluation](src/tasks/dag_evaluation)

该任务以一整张 DAG 为单位，结合题目文本、Ground Truth、完整 DAG 与实际图片，对图中所有节点给出二元判断。图片会读取本地文件并编码为多模态 `image_url` 内容发送给模型；模型不会收到图片本地路径，也不会收到 `batch_id`。

### 输入文件示例：`combine.json`

```json
[
  {
    "batch_id": "biology/example:sample_001",
    "problem_text": "Which stage is shown?",
    "ground_truths": ["The pupa stage is ..."],
    "image_paths": ["data\\download\\ready\\biology\\example.png"],
    "graph": {
      "graph_logic": {
        "conditions": [{"id": "C_1", "type": "图像信息", "content": "..."}],
        "intermediate_steps": [{"id": "I_1", "type": "逻辑推导", "content": "..."}],
        "final_conclusion": {"id": "O", "type": "综合归纳", "content": "..."}
      }
    }
  }
]
```

### 导出文件示例：`dag_evaluation.json`

```json
[
  {
    "batch_id": "biology/example:sample_001",
    "node_evaluations": [
      {"node_id": "C_1", "is_correct": true},
      {"node_id": "I_1", "is_correct": true},
      {"node_id": "O", "is_correct": false}
    ]
  }
]
```

输出必须完整覆盖输入 DAG 的 `conditions`、`intermediate_steps`、`final_conclusion` 中的全部节点，并严格保持 C → I → O 原顺序。漏评、重复、额外节点或顺序错误的结果不会被保存为 `completed`。

### YAML 与命令行接口

每个模型目录应有一份 `dag_evaluation.yaml`，其 `paths` 通常形如：

```yaml
paths:
  input_json: data/dag-reasoning-eval-1/<模型目录>/combine.json
  database: data/dag-reasoning-eval-1/<模型目录>/dag_evaluation.sqlite3
  output_json: data/dag-reasoning-eval-1/<模型目录>/dag_evaluation.json
  system_prompt: docs/prompt/dag_eval.md
```

`model` 与 `retry` 的字段含义和 `cot_to_dag.yaml` 相同。命令也与 CoT→DAG 任务一致，只是模块名不同：

```powershell
python -m src.tasks.dag_evaluation.cli run --config <dag_evaluation.yaml路径>
python -m src.tasks.dag_evaluation.cli status --config <dag_evaluation.yaml路径>
python -m src.tasks.dag_evaluation.cli retry-failed --config <dag_evaluation.yaml路径>
python -m src.tasks.dag_evaluation.cli export --config <dag_evaluation.yaml路径>
```

例如：

```powershell
python -m src.tasks.dag_evaluation.cli run `
  --config data\dag-reasoning-eval-1\gemma-4-31b-it\dag_evaluation.yaml
```

## `src/batch_engine`

目录：[src/batch_engine](src/batch_engine)

`src/batch_engine` 是两个任务模块共用的执行接口，主要由以下部分组成：

- `config.py`：加载 YAML 与根目录 `.env`，检查路径、模型、并发、流式和重试配置。
- `db.py`：使用 SQLite/aiosqlite 记录每个 `batch_id` 的 `pending`、`completed`、`failed` 状态及完成结果，用于断点续传。
- `runner.py`：把 pending 任务放入共享队列，创建不超过 `max_concurrency` 数量的 worker；任一 worker 完成当前任务后会立即领取下一条。
- `llm_client.py`：使用 LiteLLM 调用 OpenAI 兼容中转站，使用 Instructor 解析 Pydantic 结构化输出；Tenacity 负责统一重试。`min_request_interval_s` 会限制所有 worker 发起相邻请求的最小间隔。
- `exporter.py`：按任务输入 JSON 的原有顺序，导出所有已完成结果。

批处理引擎没有独立的 `python -m` 命令。实际调用方式是使用某个任务模块的 CLI，例如：

```powershell
python -m src.tasks.cot_to_dag.cli run --config <cot_to_dag.yaml路径>
python -m src.tasks.dag_evaluation.cli run --config <dag_evaluation.yaml路径>
```

新建同类批量任务时，一般在 `src/tasks/<任务名>/` 中实现适配器，并提供以下业务接口供 Batch Engine 调用：

```text
load_items(input_path)       读取并校验任务输入
get_batch_id(item)           返回唯一任务 ID
build_messages(item)         构造模型消息
output_model                 声明 Pydantic 输出模型
validate_output(output)      执行业务结果校验
export_record(id, output)    构造最终导出记录
```

这样可复用同一套 SQLite 状态管理、动态并发调度、统一重试和导出逻辑。
