# 分层样本的有序导出与元数据标注

1. 修改 `scripts/sample_shared_stratified_ids.py` 的输出记录格式：不再输出仅含字符串的 `sample_id` 列表；每个抽中题目输出一个对象：

   ```json
   {
     "sample_id": "<sample_id>",
     "subject_dir": "<学科>",
     "difficulty_level": "<难度>"
   }
   ```

2. 继续以共同 `sample_id` 的已校验元数据作为 `subject_dir` 和 `difficulty_level` 的唯一来源；不新增或猜测题目元数据。

3. 抽样完成后再排序导出。输出顺序固定为：`math`、`physics`、`circuit`、`chemistry`、`geography`、`biology`；每个学科内固定为 `medium`、`medium_high`、`high`；同一分层内按 `sample_id` 升序排列。

4. 随机种子只影响每层被选中的样本集合，不影响同一集合的导出顺序；相同输入、请求数量与种子下，输出内容和顺序均可复现。

5. 屏幕分层统计、容量不足时“已取上限”的正常完成行为保持不变；验收时检查输出对象数量、字段完整性、每条元数据与共同输入一致性，以及整体顺序符合固定分层顺序。
