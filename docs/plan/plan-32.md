# API 共同题目分层抽样脚本

1. 在 `scripts/` 新增 `sample_shared_stratified_ids.py`，只负责从 API 模型原始数据 JSON 中抽样；不读取或生成 CoT、DAG、评估结果，也不考虑 Domino-Bench 的其他数据。

2. `--input-json` 在命令行层面是可重复选项：每次只接收一个路径，调用时重复传入两个或更多 API 原始数据 JSON。解析后脚本内部将其保存为 `list[Path]`；不使用逗号分隔的字符串，也不要求用户传入 JSON 路径列表文本。使用必填 `--output-json <路径>` 指定结果文件。调用形式为：

   ```powershell
   python scripts\sample_shared_stratified_ids.py `
     --input-json <API模型1原始JSON> `
     --input-json <API模型2原始JSON> `
     --output-json <输出JSON>
   ```

3. 每个输入 JSON 顶层必须是对象列表；每条记录读取 `sample_id`、`subject_dir`、`difficulty_level`，并要求单个输入文件内的 `sample_id` 唯一。

4. 取全部输入文件 `sample_id` 的精确交集作为候选池；不使用 `problem_id`。对交集中的同一 `sample_id`，各输入中的 `subject_dir` 和 `difficulty_level` 必须一致，否则报错。

5. 在候选池中仅保留 `medium`、`medium_high`、`high` 三个难度，以及 `math`、`physics`、`circuit`、`chemistry`、`geography`、`biology` 六个 `subject_dir` 取值，组成 18 个分层；其中 `circuit` 对应论文口径中的 Engineering。

6. 默认从 18 个分层中共抽取 400 个 `sample_id`；提供可选 `--sample-size` 覆盖。按尽量均衡的配额分配：400 条时每层 22 条，额外 4 条分配至 4 个分层，使其各为 23 条。使用固定默认随机种子，并提供 `--seed` 覆盖。任一分层不足所需配额时报告该分层及可用数量并停止。

7. 输出为 JSON 字符串列表，仅包含抽中的 `sample_id`；按固定的学科、难度顺序写出，每个分层内按随机种子确定的抽样顺序排列。屏幕输出输入文件条数、交集条数、18 个分层的可用数和抽样数、总抽样数及输出路径。

8. 验收：使用 API 模型输入运行后，输出默认恰为 400 个互不重复的 `sample_id`；每个 ID 均存在于所有输入文件中，且每个分层抽取 22 或 23 条。
