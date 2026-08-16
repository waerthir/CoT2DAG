# 共同 50 题的 Grok 与 Gemini 节点评估配置

1. 对 `data/dag-quality-eval-1` 下每个模型目录各新增两份 YAML：
   - `dag_evaluation_grok.yaml`
   - `dag_evaluation_gemini.yaml`
   当前目录中的所有模型均生成，不覆盖原有 `dag_evaluation.yaml` 或其他 YAML。

2. 每份新增 YAML 以同目录既有 `dag_evaluation.yaml` 为模板，保留其模型名、API 基址、超时、并发、`completion_kwargs`、请求间隔、流式设置及重试配置；仅修改本计划指定的路径、环境变量和系统提示词字段。

3. 两类 YAML 的路径分别设置为该模型目录的独立 50 题任务路径：
   - `paths.input_json`：`data/dag-quality-eval-1/<model>/combine_50_sample.json`。
   - Grok：`paths.database` 为 `dag_evaluation_50_sample_grok.sqlite3`，`paths.output_json` 为 `dag_evaluation_50_sample_grok.json`。
   - Gemini：`paths.database` 为 `dag_evaluation_50_sample_gemini.sqlite3`，`paths.output_json` 为 `dag_evaluation_50_sample_gemini.json`。
   - 两类 YAML 的 `paths.system_prompt` 均为 `docs/prompt/dag_eval.md`。

4. 设置环境变量名称：
   - `dag_evaluation_grok.yaml`：`model.api_key_env: CODEX_2_API_API_KEY_4_EVAL_GROK`。
   - `dag_evaluation_gemini.yaml`：`model.api_key_env: CODEX_2_API_API_KEY_4_EVAL_GEMINI`。

5. 不修改任务代码、`src/batch_engine`、输入 `combine_50_sample.json`、原有 YAML 或已有数据库/导出结果。

6. 本地验证所有新增 YAML：确认每份均能由配置加载器读取；输入 JSON 与系统提示词路径存在；每个模型目录路径正确；Grok/Gemini 的数据库与输出路径相互独立；不运行 `run`，不发起 API 请求。
