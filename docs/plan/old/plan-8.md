# 抽样脚本支持 JSONL 输入计划

- 修改 `scripts/sample_reasoning_chains.py` 的输入读取函数，使其按输入文件后缀解析数据：`.json` 读取 JSON 数组，`.jsonl` 逐行读取 JSON 对象。
- JSONL 跳过空行；每个非空行继续按现有规则校验 `reasoning_chain_model`。
- 解析或校验失败时沿用脚本现有的终端错误输出方式。
- 保持抽样数量、随机种子、连续 `batch_id` 编号和 JSON 输出格式不变。
- 更新命令行帮助，说明输入支持 `.json` 与 `.jsonl`，输出仍为 JSON。
