# Sample ID 迁移与统一图级评估输入准备计划

## 1. 建立每个来源的 ID 映射清单

- 为每个 CoT/DAG 来源生成独立映射清单，包含 `old_batch_id`、`sample_id`、`source_index` 和 `match_method`。
- 对旧 `batch_id` 等于唯一 `problem_id` 的来源，以 `problem_id` 关联原始记录中的 `sample_id`；两侧 `problem_id` 必须一对一匹配，输入顺序不参与关联。
- 对发生 `problem_id` 碰撞、已使用保序自定义唯一键的特殊来源，以自定义键携带的原始序号或 `source_index` 定位原始记录，再取得对应 `sample_id`。
- 映射清单检查旧 ID 覆盖完整、每条记录恰好映射一个 `sample_id`、当前运行范围内 `sample_id` 唯一；多个模型结果合并时使用模型/运行命名空间。

## 2. 同步本地证据资源并建立资源映射

- 从原始记录按 `sample_id` 收集远程 Ground Truth 文件路径和图片路径，写入待同步资源清单。
- 下载/同步清单中的 Ground Truth 文件与图片到本地；以远程完整路径的稳定哈希加原扩展名命名，复用重复引用的资源。
- 写出本地资源映射清单：`sample_id`、本地 Ground Truth 文件路径、本地图片相对路径及对应远程来源路径。
- Ground Truth 文件下载完成后，读取其本地内容，抽取题目文本和 Ground Truth 文本列表；具体字段名以本地样本文件的实际结构确定。

## 3. 生成统一图级评估输入文件

- 使用 `sample_id` 关联迁移后的 DAG、资源映射和本地 Ground Truth 内容，生成单一 JSON 列表文件。
- 每条统一记录包含一张图完成评估所需的全部信息：

  ```json
  {
    "batch_id": "<sample_id>",
    "problem_text": "...",
    "ground_truths": ["..."],
    "image_paths": ["evidence/images/abc.png"],
    "graph": {"graph_logic": {}}
  }
  ```

- `batch_id` 仅作为 Batch Engine、SQLite 和导出的内部标识；模型消息不发送该字段，也不发送本地图片路径。
- 汇总检查每个 `sample_id` 恰好关联一张 DAG、一份可解析的 Ground Truth 内容和所需本地图片；缺失、重复或多重匹配时终端报错结束。

## 4. 批处理评估衔接

- 图级 Adapter 只读取统一评估输入文件，以 `sample_id` 作为任务 ID。
- Adapter 将 `problem_text`、`ground_truths` 和完整 `graph` 序列化到模型文本消息，并读取 `image_paths` 将实际图片内容附带到多模态消息。
- 模型返回整图 `node_evaluations`；Exporter 将内部 `sample_id` 与结果合并输出。
