# 人工 A/B 标注、机器判断与第三人裁决工作清单合并

1. 在 `scripts/` 新增合并脚本，使用四个位置参数：
   ```powershell
   python scripts\merge_claim_judgments.py <annotator-a-json> <annotator-b-json> <machine-judge-json> <output-json>
   ```
   前两个输入分别为人工标注者 A、B 的节点二值判断 JSON；第三个输入为机器判断大表 JSON。三份文件均按现有图级节点评估导出格式读取，例如 `data/dag-quality-eval-1/gemma-4-31b-it/dag_evaluation_50_sample_gemini.json` 或 `dag_evaluation_50_sample_grok.json`。

2. 每份输入读取顶层图记录的 `batch_id`，以及 `node_evaluations` 内的 `node_id` 和 `is_correct`。检查 `batch_id` 唯一、同一图内 `node_id` 唯一、`is_correct` 为布尔值；以 `(batch_id, node_id)` 建立标签集合。

3. 以人工 A 的图记录及节点顺序为输出顺序，并要求人工 B 的 `(batch_id, node_id)` 集合与人工 A 完全一致。人工 A/B 的共同键集合是本次合并的唯一目标集合。

4. 机器判断 JSON 作为可包含额外图和节点的大表处理：为其建立完整 `(batch_id, node_id)` 到机器标签的映射，再只按人工 A/B 的共同键集合查找机器判断。机器表中未被 A/B 引用的额外记录直接忽略；若其缺少任一 A/B 所需键，或任一输入存在重复键，则汇总报告并报错退出，不写出部分结果。

5. 对每个对齐节点仅保留五个判断字段，并保留 `node_id` 作为结构对齐键：
   ```json
   {
     "node_id": "C_2",
     "annotator_a_is_correct": true,
     "annotator_b_is_correct": true,
     "machine_is_correct": true,
     "requires_third_annotator": false,
     "third_annotator_is_correct": null
   }
   ```
   顶层仍按 `batch_id` 分组，形成与现有评估结果相近的图列表 JSON，便于后续人工填写第三人标签。

6. A/B 相同时，设置 `requires_third_annotator: false`，并将 `third_annotator_is_correct` 保留为 `null`。A/B 不同时，保留两人的原始标签，设置 `requires_third_annotator: true`，并将 `third_annotator_is_correct` 设为 `null`，等待第三人填写。

7. 输出文件是第三人裁决工作清单，而不是最终人工金标。第三人完成标注后，仅将需要裁决节点的 `third_annotator_is_correct` 填为二值值。后续统计脚本按以下规则即时推导最终 Human 标签：`requires_third_annotator` 为 `false` 时，使用已确认相等的 A/B 标签；为 `true` 时，使用 `third_annotator_is_correct`。若需要第三人但该字段仍为 `null`，统计脚本报错。

8. 输出 JSON 顶层包含输入路径、机器判断来源、汇总计数（总节点数、A/B 一致数、A/B 分歧数、待第三人裁决数、机器大表总节点数、机器表中未引用节点数）及按 `batch_id` 排列的节点记录。通过临时文件原子写入。

9. 本地验证使用同一模型、同一 50 题的 A/B 标注文件和包含额外记录的机器判断大表：验证 A/B 严格键集合对齐、按 A 的顺序输出、机器额外记录被忽略、机器缺少 A/B 所需节点时报错、A/B 一致或分歧时 `requires_third_annotator` 的正确设置、第三人字段初始为 `null`；不发起 API 请求。
