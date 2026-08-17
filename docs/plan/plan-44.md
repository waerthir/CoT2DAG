# 计算人工验证的 Claim Correct Rate 与 Judgment Agreement

1. 在 `scripts/` 新增一个统计脚本（建议名：`calculate_claim_judgment_metrics.py`），接收一个位置参数：人工裁决完成后的 JSON 路径，例如：
   ```powershell
   python scripts\calculate_claim_judgment_metrics.py `
     data\dag-quality-eval-1\gemma-4-31b-it\dag_evaluation_50_sample_human.json
   ```
   本轮只读取该文件，不修改输入数据，也不调用 API。

2. 严格读取顶层 `records`，以 `(batch_id, node_id)` 作为 claim 唯一键；检查 `batch_id`、同图内 `node_id` 不重复，且 A、B、机器标签均为布尔值。对 `requires_third_annotator: true` 的节点，要求 `third_annotator_is_correct` 已是布尔值；仍为 `null` 或类型错误时，报告具体键并退出，不输出部分统计。

3. 对每个 claim 即时生成最终 Human 标签：A/B 原本一致时使用共同的 `annotator_a_is_correct`／`annotator_b_is_correct`；要求第三人裁决时使用 `third_annotator_is_correct`。若标记为无需第三人但 A/B 不一致，同样视为输入结构错误。

4. 以全部 claim 为分母，计算论文表 V 对应的五个指标：
   - `human_claim_correct_rate`：最终 Human 标签为 `true` 的比例；
   - `judge_claim_correct_rate`：`machine_is_correct` 为 `true` 的比例；
   - `human_human_raw_agreement`（H–H）：A、B 标签完全相同的比例，第三人裁决不改变此原始一致率；
   - `human_human_cohens_kappa`（H–H Cohen’s κ）：用 A、B 的二元标签计算观察一致率与按各自标签边际比例得到的随机一致率；
   - `judge_human_agreement`（J–H）：机器标签与最终 Human 标签完全相同的比例。
   除 Cohen’s κ 外均以百分比输出；κ 保持 `[-1, 1]` 的原始数值。若 κ 的分母为零，输出 `null` 并在屏幕说明该样本的边际分布使 κ 不可定义。

5. 将结果以单个 JSON 对象打印到标准输出，至少包括输入路径、总题数、总 claim 数、A/B 分歧数、第三人裁决数，以及上述五项指标；不默认创建文件。需要保留结果时由调用方使用 PowerShell 重定向保存。

6. 验收时用一份已完成第三人裁决的 `dag_evaluation_50_sample_human.json` 运行，核对总 claim 数与文件一致；随机复算 A/B 一致数、最终 Human 正确数和机器—Human 一致数；并确认含待裁决 `null`、重复键或非布尔标签的输入会明确失败。
