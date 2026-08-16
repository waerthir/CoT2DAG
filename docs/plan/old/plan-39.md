# 人工一致性验证的共同 50 题名单

1. 在 `scripts/` 新增脚本，命令行接收：
   - `--input-json`：200 条共同随机样本的统计 JSON，例如 `data/dag-quality-eval-1/gemma-4-31b-it/dag_quality_evaluation_200_random.json`。
   - `--output-json`：50 题共同名单的输出路径，计划使用 `data/dag-quality-eval-1/shared_human_agreement_50_random.json`。
   - `--sample-count`：二次随机抽样数量，默认 `50`。
   - `--seed`：固定随机种子，保证名单可复现。

2. 读取输入 JSON 的 `selected_items`；确认其为对象列表，`batch_id` 非空且唯一，并确认条目数量不少于 `sample-count`。不读取或重新计算输入文件中的 `statistics`。

3. 在全部 200 条 `selected_items` 中按固定种子无放回随机抽取 50 条；抽中后按输入文件中的原始 `selected_items` 顺序重新排序，以保持共同题目名单的稳定展示顺序。

4. 输出 JSON 至少包含：源文件路径、随机种子、目标抽样数、实际抽样数，以及完整保留的 `selected_items`。每条名单保留原有的 `batch_id`、`subject_dir`、`difficulty_level` 与 `selection_score`，供所有模型后续使用同一组问题。

5. 本地验证：使用指定的 `gemma-4-31b-it/dag_quality_evaluation_200_random.json` 生成 50 题名单；确认抽中 `batch_id` 全部来自输入的 200 条、无重复、固定种子重复运行结果一致，且输出文件位于 `data/dag-quality-eval-1` 根目录。不发起 API 请求。
