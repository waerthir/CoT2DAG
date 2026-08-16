# DAG 质量评估批处理任务

1. 新增与 `cot_to_dag`、`dag_evaluation` 平级的 `src/tasks/dag_quality_evaluation/`，包含 `schemas.py`、`adapter.py`、`cli.py`、`__init__.py`；不修改 `src/batch_engine`。

2. 输入适配器读取 `combine_cot_dag_400_sample.json` 这类顶层列表。每条必须包含唯一、非空的 `batch_id`、非空的 `reasoning_chain_model` 和对象类型的 `graph`；不读取题干、Ground Truth、图片或抽样附加元数据。

3. `batch_id` 仅由适配器用于任务注册、数据库读取和导出关联，不发送给模型。每次请求向 `docs/prompt/dag_quality_eval.md` 发送一条输入记录中的 `reasoning_chain_model` 与 `graph`，用户消息为：

   ```json
   {
     "reasoning_chain_model": "<完整原始 CoT>",
     "graph": {}
   }
   ```

   系统提示词和用户消息均不加入题干、Ground Truth、图片或其他评估材料；同步修正 `docs/prompt/dag_quality_eval.md` 的输入示例，移除其中的 `batch_id`。

4. 定义 Pydantic 输出模型：图级 `Information_Coverage` 与逐节点 `node_evaluations`。所有分数限制在 0 至 10；节点均有 `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`，I/O 节点另有 `Dependency_Completeness`、`Dependency_Correctness`。

5. 在适配器内从 `graph.graph_logic` 提取 C、I、O 节点的预期 ID 与层级，校验模型输出：节点不得遗漏、重复或新增，顺序必须为 C → I → O；C 节点不得包含两项 Dependency 分数，I/O 节点必须包含两项 Dependency 分数。无需新增独立校验模块。

6. `export_record()` 保留模型的逐节点结果，并由程序计算 `dag_evaluation`：
   - `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`：全部 C/I/O 节点对应分数的算术平均值；
   - `Dependency_Completeness`、`Dependency_Correctness`：全部 I/O 节点对应分数的算术平均值；
   - `Information_Coverage`：直接使用模型输出的图级分数；
   - 五项平均值保留两位小数。

   ```json
   {
     "batch_id": "<batch_id>",
     "node_evaluations": [],
     "dag_evaluation": {
       "Information_Fidelity": 0.0,
       "Claim_Atomicity": 0.0,
       "Node_Type_Correctness": 0.0,
       "Dependency_Completeness": 0.0,
       "Dependency_Correctness": 0.0,
       "Information_Coverage": 0.0
     }
   }
   ```

7. CLI 沿用标准 `run`、`status`、`retry-failed`、`export` 命令和 YAML 配置方式。每个模型/项目目录各自放置本任务 YAML（建议命名 `dag_quality_evaluation.yaml`），与现有 `cot_to_dag.yaml`、`dag_evaluation.yaml` 并列；任务代码不硬编码输入 JSON、提示词、数据库或输出 JSON 路径。

   ```yaml
   paths:
     input_json: <该项目的 combine_cot_dag_400_sample.json>
     database: <该项目的独立 SQLite 路径>
     output_json: <该项目的质量评估导出 JSON 路径>
     system_prompt: <质量评估提示词路径>
   ```

   `model`、`retry`、`max_concurrency`、`timeout_s`、`stream` 等配置同样由 YAML 提供，并与同目录现有任务 YAML 的配置结构保持一致。

8. 发送内容以 `docs/prompt/dag_quality_eval.md` 的最终 `# Input` 约定为唯一依据：适配器从 YAML 的 `system_prompt` 加载系统提示词，用户消息只 JSON 序列化 `reasoning_chain_model` 和 `graph`；提示词输入示例同步保持同一字段结构，不发送 `batch_id`。

9. 验收：不发起真实 API 请求；对真实抽样输入做本地加载校验，并以构造的合法/非法输出验证节点顺序、C/I/O 指标字段限制、分数范围和六项导出聚合结果。
