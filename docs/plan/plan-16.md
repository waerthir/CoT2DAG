# Problem ID 到批处理 CoT 输入转换计划

- 新建 `scripts/extract_problem_id_reasoning_chains.py`，使用两个命令行位置参数指定输入 JSON 路径与输出 JSON 路径。
- 读取顶层为列表的输入 JSON；实际样例的每个对象包含字符串 `problem_id` 和 `reasoning_chain_model`。
- 按输入原始顺序逐项输出，仅保留并重命名所需字段：

  ```json
  [
    {
      "batch_id": "open_078ef52a7df867ddddd53f5a",
      "reasoning_chain_model": "..."
    }
  ]
  ```

- 将 `problem_id` 的值写入 `batch_id`；保留 `reasoning_chain_model` 原文，不处理其余字段。
- 输入不是列表、列表元素不是对象、缺少所需字段、字段不是字符串，或输出路径与输入路径相同时，在终端报错并结束。
