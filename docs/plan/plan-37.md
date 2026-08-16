# DAG 质量评分节点输出 Schema 对齐

1. 修改 `src/tasks/dag_quality_evaluation/schemas.py`，将当前统一的 `QualityNodeEvaluation` 拆为两类严格节点模型：
   - C 节点评分：`node_id` 必须匹配 `C_*`，仅包含 `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`；禁止额外字段。
   - I/O 节点评分：`node_id` 必须匹配 `I_*` 或 `O_*`，必须同时包含上述三项及 `Dependency_Completeness`、`Dependency_Correctness`；禁止额外字段。

2. 将 `DAGQualityEvaluationOutput.node_evaluations` 改为上述两类节点模型的联合列表，保持现有单一数组、字段名称和 JSON 输出格式不变。

3. 调整 `adapter.py` 的类型使用与导出聚合，使其接受联合节点模型；保留现有从输入 `graph.graph_logic` 提取 C → I → O 节点、逐项核对完整 ID 列表和层级顺序的校验。

4. 删除仅因 C 节点携带 `null` Dependency 字段而产生的后置兼容性判断；C 节点出现 Dependency 字段、I/O 节点缺少 Dependency 字段，均由严格 Schema 直接判为无效结构化输出。

5. 保持 `docs/prompt/dag_quality_eval.md` 当前的 C/I/O 输出说明和所有 YAML 不变；不修改 `src/batch_engine`。

6. 仅做本地验证：验证合法 C/I/O 输出可解析；验证 C 节点带 Dependency 字段、I/O 节点缺 Dependency 字段、错误 ID 前缀和越界分数均被拒绝；验证真实输入仍可加载、节点顺序校验与六项导出聚合正常。不发起真实 API 请求。
