# 以 DAG combine 为主的 CoT 拼接规则

1. 修改 `scripts/build_cot_dag_combine.py` 的命令行接口，改用三个必填具名参数：`--dag-json <路径>`、`--source-json <路径>`、`--output-json <路径>`。参数含义由选项名明确指定，输入文件名不参与角色判断。

   ```powershell
   python scripts\build_cot_dag_combine.py `
     --dag-json <含 batch_id 和 graph 的 DAG JSON 路径> `
     --source-json <含 sample_id 和 reasoning_chain_model 的原始数据 JSON 路径> `
     --output-json <输出 JSON 路径>
   ```

2. DAG JSON 是设计上的 `combine` 目标集合，而非名称为 `combine.json` 的文件：使用其中的 `batch_id` 决定输出记录及输出顺序。

3. 保持 DAG 输入校验：每条 DAG 记录必须有唯一、非空的 `batch_id` 和对象类型的 `graph`。

4. 扫描原始数据 JSON 时，仅处理 `sample_id` 属于 DAG `batch_id` 集合的记录：
   - 匹配记录必须有非空的 `reasoning_chain_model`；
   - 同一目标 `sample_id` 出现多次时明确报错；
   - 原始数据中 `sample_id` 不在 DAG 集合内的记录全部忽略，不因其数量、字段缺失或重复而报错。

5. 遍历 DAG `batch_id`，若任一 ID 没有匹配的原始 `sample_id`，打印全部缺失 ID 并停止，不写出结果；不再因原始数据存在额外 ID 而停止。

6. 保持输出结构、`batch_id` 原值和 DAG 原始顺序不变；输出条数恒等于 DAG JSON 条数。屏幕输出 DAG 条数、成功合并条数及被忽略的原始记录条数。

7. 验收：构造或选用一份原始数据比 DAG 输入多记录的情况，确认额外原始记录不进入输出且运行成功；删除一个 DAG 所需的原始记录，确认脚本列出该 `batch_id` 并拒绝写出输出文件。
