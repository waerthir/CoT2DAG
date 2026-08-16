# 对 A/B 分歧节点进行第三方内容裁决

1. 以 `data/dag-quality-eval-1/<model>/dag_evaluation_50_sample_human.json` 为每个模型的裁决工作清单，仅处理同时满足以下条件的节点：
   ```json
   "requires_third_annotator": true,
   "third_annotator_is_correct": null
   ```
   当前待处理数量为 324：Gemma-4-31B-it 39、GLM-4.1V-9B 44、GLM-5V-Turbo 49、GPT-5.6-sol-xhigh 32、InternVL3.5-38B 64、LLaVA-CoT-11B 38、Metis-RISE-72B 34、NVLM-D-72B 24。

2. 对每个工作清单，以 `batch_id` 在同目录 `combine_50_sample.json` 中定位题目记录；再以 `node_id` 在 `graph.graph_logic.conditions`、`intermediate_steps`、`final_conclusion` 中定位待裁决节点。开始写入前检查每个待裁决节点都能唯一定位到对应题目和 DAG 节点；缺失、重复或结构不一致时报告并停止该模型的写入。

3. 从同一题目记录的 `image_paths` 获取附图，不进行远程下载：路径为本地路径；相对路径以项目根目录为基准解析。对需要图像证据的节点，读取该题 `image_paths` 中的全部实际图片；没有 `image_paths` 的题目不读取图片。

4. 对每个待裁决节点，读取 `problem_text`、`ground_truths`、完整 `graph`、节点 `content`，以及按上一项确定的本地图片。使用 `docs/prompt/dag_eval.md` 的二值判定规则：
   - C 层文字信息按题目文本、Ground Truth 或可靠文本证据核验；
   - C 层图像信息必须按实际图片的可见内容核验；
   - C 层学科常识按可靠学科事实核验；
   - I/O 节点只判断 `content` 表达的结论本身是否成立；当其内容依赖图像事实时，同样读取实际图片核验；不因父节点错误、依赖不足或 `reasoning_logic` 不严密而扣为 false。
   A/B 与机器的既有标签仅用于识别待裁决节点，不作为裁决证据。

5. 对全部待裁决节点作最终二值判断，并将 `third_annotator_is_correct` 直接写为 `true` 或 `false`。不保留 `null`。保留 `annotator_a_is_correct`、`annotator_b_is_correct`、`machine_is_correct`、`requires_third_annotator`、`node_id`、图顺序和其他原有 JSON 内容，不新增评分字段，不覆盖非空的第三方标签。

6. 每个模型通过临时文件写完后原子替换原工作清单。

7. 写入后重新校验每个模型：原始待裁决节点数不变；所有本轮已裁决节点的 `third_annotator_is_correct` 均为布尔值；不存在仍为 null 的待裁决节点；其他节点字段与写入前一致。输出每个模型的 true/false 数量。

8. 不调用外部模型 API，不修改 `src/batch_engine`、DAG、机器判断或 A/B 初始标签；只对上述工作清单中的 `third_annotator_is_correct` 作局部写入。
