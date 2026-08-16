# 抽样脚本跳过坏记录计划

- 修改 `scripts/sample_reasoning_chains.py` 的输入解析与单条记录校验：遇到不合规记录时跳过并继续读取后续记录。
- JSONL 中无法解析的非空行跳过；JSON 数组或 JSONL 中不是对象、缺少有效 `reasoning_chain_model` 的记录跳过。
- 在终端输出跳过记录的数量；抽样只使用通过校验的记录。
- 输入文件不存在、后缀不支持、整个 `.json` 文件无法解析或 JSON 顶层不是数组时，继续使用终端错误信息结束运行。
- 保持随机抽样、`batch_id` 编号和 JSON 输出格式不变。
