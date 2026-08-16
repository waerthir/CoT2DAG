# Ground Truth Claim 类型处理计划

- `scripts/build_dag_combine.py` 继续从 `ready3_open_rewrite.claim_split.claims` 按原顺序提取每项的 `claim`，写入 `ground_truths: list[str]`。
- 当前不将 `claims[].label` 写入 `combine.json`，也不发送给 DAG 节点评估模型。
- `docs/prompt/dag_eval.md` 已按 DAG 节点层级和节点 `type` 规定判据：C 层分别依据文本、图片或学科常识；I/O 层统一依据父节点、`reasoning_logic` 与相关证据判断。`claims[].label` 不参与该判据选择。
- 保持现有 `ground_truths` 的字符串列表结构，避免 `reasoning`、`perception` 等未在提示词中定义用途的元数据影响 Ground Truth 的语义匹配与 `is_correct` 判定。
- Ground Truth 原始 JSON 保留完整 claim 对象；后续若评估 prompt 明确规定 label 的用途，再单独增加对应字段与输入规则。
