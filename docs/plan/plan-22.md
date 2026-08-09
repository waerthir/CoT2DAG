# Sample ID 迁移与图级评估证据准备计划

## 1. 建立每个来源的 ID 映射清单

- 为每个 CoT/DAG 来源生成独立映射清单，包含 `old_batch_id`、`sample_id`、`source_index` 和 `match_method`。

  ```json
  {
    "old_batch_id": "open_xxx__row_000001",
    "sample_id": "biology/dataset:sample:open_xxx",
    "source_index": 1,
    "match_method": "source_index"
  }
  ```

- 对 `old_batch_id` 等于原始 `problem_id` 的来源：以 `problem_id` 关联原始记录中的 `sample_id`；要求两侧 `problem_id` 均唯一且一对一匹配，输入顺序不作为关联依据。
- 对发生 `problem_id` 碰撞、已使用保序自定义唯一键的特殊来源：以自定义键携带的原始序号或记录的 `source_index` 定位原始记录，再取得对应 `sample_id`；要求原始记录数、序号范围和每个位置的来源 ID 均一致。
- 映射清单生成时检查：每个旧 ID 恰好映射一个 `sample_id`，每个 `sample_id` 在当前运行范围内唯一，所有输入记录均被覆盖；不满足时终端报错结束。
- 多个模型/运行合入同一数据库或同一导出文件时，以模型或运行名为 `sample_id` 增加命名空间，避免同一题目在不同模型输出中的 ID 再次碰撞。

## 2. 使用映射清单迁移派生数据

- 读取映射清单，将 CoT 和 DAG 图记录中的 `batch_id` 从 `old_batch_id` 改为 `sample_id`，保持记录顺序和其他字段不变，写入新的迁移结果文件。
- 以迁移后的 DAG 重新生成节点与关系记录，使节点/关系 ID 自动使用 `<sample_id>-<node_id>`。
- 为迁移后的批次使用新的 SQLite 数据库和新的导出路径，保证任务状态、DAG、节点、关系和评估结果使用同一套 `sample_id`。

## 3. 定向同步 Ground Truth 与图片

- 从已关联的原始记录中收集每个 `sample_id` 对应的远程 Ground Truth 文件路径和图片路径，生成待同步清单。
- 使用远程访问方式将清单中的文件下载/同步到本地；Ground Truth 文件和图片均按远程完整路径的稳定哈希命名，避免同名文件覆盖，并复用重复引用的同一远程文件。
- 写出本地证据映射清单，包含 `sample_id`、远程路径和本地相对路径。
- 从本地 Ground Truth 文件提取 `problem_text` 与 Ground Truth 文本列表，结合本地图片路径形成图级证据记录。

## 4. 汇总图级评估输入

- 以 `sample_id` 关联迁移后的 DAG 和本地证据映射；每张 DAG 输出一条评估输入记录：

  ```json
  {
    "batch_id": "<sample_id>",
    "problem_text": "...",
    "ground_truths": ["..."],
    "image_paths": ["evidence/images/abc.png"],
    "graph": {"graph_logic": {}}
  }
  ```

- 汇总时检查每个 `sample_id` 恰好关联一张 DAG、一组 Ground Truth 和所需图片；本地文件缺失、多重匹配或未覆盖记录时终端报错结束。
- 图级 Adapter 使用 `sample_id` 作为 Batch Engine 任务 ID；模型消息仅携带题目文本、Ground Truth、完整 DAG 和实际图片内容，Exporter 再将 `sample_id` 与整图 `node_evaluations` 合并输出。
