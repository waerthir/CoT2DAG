# DAG 图级评估资源整理计划

## 目标文件

- 对 `data\dag-reasoning-eval-1\<模型目录>\dag.json` 逐个生成同目录的 `combine.json`。
- 每条输出保持 DAG 原有顺序：

  ```json
  {
    "batch_id": "<sample_id>",
    "problem_text": "...",
    "ground_truths": ["..."],
    "image_paths": ["data/download/ready/..."],
    "graph": {"graph_logic": {}}
  }
  ```

## 新建整理脚本

- 新建 `scripts/build_dag_combine.py`。
- 每次处理一个模型目录；命令行显式提供：`dag.json` 路径、对应的原始记录 JSON 路径、ID 对齐方式和输出 `combine.json` 路径。
- 原始记录从其现有字段读取：`problem_id`、`sample_id`、`question`、`image_path`、`image_paths`、`item_path`。

## DAG 与原始记录对齐

- `problem_id` 对齐方式：建立原始记录的 `problem_id → 记录` 索引；对每条 DAG 用其原 `batch_id` 查找记录，再将输出 `batch_id` 写为该记录的 `sample_id`。
- 顺序注入方式：保持两个输入列表的原始顺序；第 `i` 条 DAG 使用第 `i` 条原始记录的 `sample_id` 和其余题目资源字段。处理前检查两个列表长度相同。
- 每个模型在执行前明确采用其中一种方式；不在脚本内猜测或混用两种对齐规则。

## 输出字段组装

- `batch_id`：使用已对齐原始记录的 `sample_id`。
- `problem_text`：使用原始记录的 `question`。
- `graph`：原样使用对应 DAG 条目的 `graph`。
- `image_paths`：优先读取 `image_paths`；为空时使用 `image_path` 组成单元素列表；去重但保持原始顺序。
- 对每个远程图片路径，移除其 `/home/lijingyue/qiujianbo/ready/` 前缀并改写为 `data/download/ready/<剩余路径>`。

## Ground Truth 组装

- 由原始记录的 `item_path` 定位该题的 Ground Truth JSON；将远程前缀 `/home/lijingyue/LiangEnRui/` 改写为本地前缀 `data/download/`。
- 从 Ground Truth JSON 读取 `ready3_open_rewrite.claim_split.claims`。
- 保持 `claims` 原始顺序，提取每个 claim 对象的 `claim` 字段，组成输出的 `ground_truths` 字符串列表。

## 输出前检查

- 对齐失败、缺少 `sample_id`、本地 Ground Truth 文件不存在、`ready3_open_rewrite.claim_split.claims` 或其中的 `claim` 字段缺失、图片路径不在既定远程根目录下时，报告对应模型、DAG 序号和原 `batch_id`，并停止该模型的输出写入。
- 成功时写出完整 JSON 列表，并打印 DAG 条目数与 `combine.json` 条目数。

## 执行顺序

1. 为每个模型指定原始记录 JSON 与 ID 对齐方式。
2. 执行脚本生成 `combine.json`。
3. 抽查 `batch_id`、题目、Ground Truth、图片路径和 `graph` 是否来自同一原始记录。

## 建议

- 图片路径固定改写为 `data/download/ready/...`；Ground Truth 的 `item_path` 固定改写为 `data/download/English_remaining_ready123/items/...`。两套规则独立执行，不互相转换。
