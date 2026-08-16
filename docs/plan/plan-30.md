# CoT 与 DAG 拼接脚本

1. 在现有 `scripts/` 目录新增 `build_cot_dag_combine.py`。命令行依次接收 DAG JSON 路径、原始数据 JSON 路径和输出 JSON 路径；输出路径（包括文件名）为必填参数，不设默认输出名。脚本不调用模型或批处理引擎。输入文件只要求为 JSON，不要求文件名为 `combine.json`、`translated.json` 或其他固定名称。

2. 读取两个顶层 JSON 列表：
   - DAG JSON 记录要求包含 `batch_id` 与 `graph`；其余已有字段不写入新文件；
   - 原始数据 JSON 记录要求包含 `sample_id` 与 `reasoning_chain_model`。

3. 分别检查 DAG `batch_id` 和原始记录 `sample_id` 的唯一性。以 `DAG batch_id = 原始记录 sample_id` 精确匹配；两侧 ID 集合不完全一致时打印缺失/多余 ID 并停止，不按数组下标或 `problem_id` 拼接。

4. 按 DAG JSON 的原始顺序写出至命令行显式指定的输出 JSON。每条记录保留 DAG 中原始的 `batch_id`，从对应原始记录写入 `reasoning_chain_model`，并保留其 `graph`。

   ```json
   {
     "batch_id": "<原 batch_id>",
     "reasoning_chain_model": "<CoT>",
     "graph": {
       "graph_logic": {}
     }
   }
   ```

5. 使用临时文件完成写入后替换目标文件，并在屏幕输出原始记录条数、DAG 条数、合并条数及输出路径。

6. 验收：针对任意满足字段要求的 DAG JSON 与原始数据 JSON 运行；输出条数与两侧输入一致、输出顺序与 DAG 文件一致、每条同时含 CoT 与图，且输出 `batch_id` 与 DAG `batch_id`（亦即原始记录 `sample_id`）保持不变。
