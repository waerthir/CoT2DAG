# DAG 质量评分分层抽样与统计脚本

1. 在 `scripts/` 新增脚本。命令行接收：
   - `--input-json`：单个模型的 DAG 质量评估导出 JSON，例如 `data/dag-quality-eval-1/gemma-4-31b-it/dag_quality_evaluation.json`。
   - `--selection-json`：分层元数据文件，例如 `data/dag-quality-eval-1/shared_sample_ids_per_stratum_22.json`，提供 `sample_id`、`subject_dir`、`difficulty_level`。
   - `--output-json`：汇总抽样与统计结果的 JSON 路径。
   - `--mode best` 或 `--mode random`：分别按质量最高或随机方式抽样；随机模式支持可选固定随机种子。
   - `--sample-count`：总抽样数，默认 `200`。

2. 使用输入 JSON 的 `batch_id == selection-json` 中的 `sample_id` 关联分层元数据；只将既有质量评估记录且可找到分层信息的条目纳入候选池。缺失关联、重复 ID 或评分字段不完整时明确报告，不静默混入抽样。

3. 将 `subject_dir × difficulty_level` 视为一个层，并从单个输入 JSON 中抽取 `sample-count` 条样本：先在各层平均分配基础配额，余数按分层元数据中的稳定顺序分配，使各层数量最多相差 1。任一层候选数少于其分配配额时，报告该层的需求数和可用数并报错退出；不跨层补配，也不输出少于目标总数的抽样结果。

4. `best` 模式按每张图 `dag_evaluation` 内六项分数的算术平均值从高到低选择；同分时按 `batch_id` 排序，保证可复现。`random` 模式在每层候选中随机选择，并在提供种子时保证可复现。

5. 对最终抽样结果统计均值、通过数量、总数量和通过率；通过阈值固定为分数 `>= 6.0`：
   - `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`：直接汇总全部 C/I/O 节点的对应逐节点分数。
   - `Dependency_Completeness`、`Dependency_Correctness`：直接汇总全部 I/O 节点的对应逐节点分数。
   - `Information_Coverage`：直接汇总每张抽中图的图级分数。
   - 不用“先按图平均、再按图平均”的方式替代节点级统计。

6. 输出 JSON 至少包含：脚本参数、实际抽样数量、各层目标/可用/抽中数量、每条抽中记录的 `batch_id`、`subject_dir`、`difficulty_level` 与用于 `best` 排序的图级平均分，以及六项指标的统计结果。输出顺序按分层元数据顺序和层内 `batch_id` 稳定排列。

7. 本地验证使用现有 `data/dag-quality-eval-1` 数据：检查 `best` 与带固定种子的 `random` 均可复现、输出总数严格等于 `sample-count`、分层配额正确、分层候选不足时明确报错、五项节点统计与一项图级统计的分母正确；不发起 API 请求。
