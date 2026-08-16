# 按共同 50 题名单切分 combine 数据

1. 在 `scripts/` 新增脚本，使用三个位置参数：
   ```powershell
   python scripts\filter_combine_by_sample_list.py <sample-list-json> <source-combine-json> <output-json>
   ```
   - 第一个参数：50 题共同名单，例如 `data/dag-quality-eval-1/shared_human_agreement_50_random.json`。
   - 第二个参数：单个模型的源 `combine.json`，例如 `data/dag-quality-eval-1/gemma-4-31b-it/combine.json`。
   - 第三个参数：切分后的输出路径，例如 `data/dag-quality-eval-1/gemma-4-31b-it/combine_50_sample.json`。

2. 从名单 JSON 的 `selected_items` 读取有序 `batch_id` 列表；检查列表非空、每项为对象、`batch_id` 非空且唯一。

3. 读取源 `combine.json` 顶层列表；检查每项为对象、`batch_id` 非空且唯一。以 `batch_id` 建立源记录映射。

4. 按名单中 `selected_items` 的顺序逐项取出源记录，完整保留源记录原有字段，不合并名单元数据，不改写任何字段。源文件中不在名单内的记录直接忽略。

5. 若名单中的任一 `batch_id` 在源 `combine.json` 中缺失，报告全部缺失 ID 并报错退出，不写出部分结果。成功时输出记录数必须与名单数量一致，因此各模型生成的 50 条文件拥有相同的 `batch_id` 集合和顺序。

6. 使用临时文件写完后再原子替换输出 JSON；命令结束时打印名单数、输出数和忽略的源记录数。

7. 本地验证使用 `gemma-4-31b-it` 的 `combine.json`：验证输出严格为 50 条、每条完整保留源记录、输出 `batch_id` 顺序严格等于共同名单顺序、名单内无缺失且源文件额外记录未输出。不发起 API 请求。
