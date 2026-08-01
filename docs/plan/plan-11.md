# 抽样脚本全采样模式计划

- 在 `scripts/sample_reasoning_chains.py` 增加 `--all`；它与 `--count` 互斥。
- `--all` 按输入中的有效记录原始顺序生成全部输出，不进行随机抽样；`batch_id` 按输出顺序连续编号，编号宽度按有效记录总数确定。
- JSONL 坏行、非对象记录和缺少有效 `reasoning_chain_model` 的记录继续跳过；全采样模式在终端打印每条跳过记录的位置与原因，并输出最终跳过数量。
- 保持 `.json` / `.jsonl` 输入支持和 JSON 数组输出格式；文件级输入错误继续在终端报错结束。
- `--count` 模式保留现有随机抽样和 `--seed` 行为；`--all` 模式不接受 `--seed`。
