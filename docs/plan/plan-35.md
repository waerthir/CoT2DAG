# 按共同样本 ID 截取源 JSON 子集脚本

1. 在 `scripts/` 新增 `filter_source_by_sample_ids.py`。脚本只读取两个 JSON 并写出源文件子集，不调用模型、网络、数据库或批处理引擎。

2. 命令行使用三个必填具名参数：

   ```powershell
   python scripts\filter_source_by_sample_ids.py `
     --selection-json <抽样ID_JSON路径> `
     --source-json <源_JSON路径> `
     --output-json <子集_JSON路径>
   ```

3. `--selection-json` 接收与 `shared_sample_ids_per_stratum_22.json` 相同的顶层列表。每条抽样记录必须是对象并包含唯一、非空的 `sample_id`；`subject_dir` 和 `difficulty_level` 不参与筛选。

4. `--source-json` 接收与 `combine_cot_dag.json` 相同的顶层对象列表。每条源记录必须包含唯一、非空的 `batch_id`；在该源格式中，`batch_id` 视为对应的 `sample_id`。

5. 以 `selection.sample_id = source.batch_id` 精确匹配。所有抽样 ID 必须在源文件中找到；缺失时列出 ID 并停止，不写出结果。源文件中未被抽中的记录直接忽略。

6. 输出为源记录的未修改子集：保留每条源记录的所有原有字段和值，不新增抽样文件中的字段；输出顺序严格保持源 JSON 的原始顺序，而非抽样文件顺序。

7. 使用同目录临时文件完成写入后替换正式输出，并打印抽样 ID 数、源记录数、输出记录数和输出路径。

8. 验收：使用 `data/dag-quality-eval-1/shared_sample_ids_per_stratum_22.json` 与一个模型的 `combine_cot_dag.json` 运行；输出条数等于抽样 ID 数，每条输出 `batch_id` 属于抽样集合，且所有字段与对应源记录完全一致。
