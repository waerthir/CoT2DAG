# CoT 翻译状态统计计划

- 新建 `scripts/count_cot_translation_status.py`，固定读取 `data/cot-3/gemini-3.1-pro-process1_translated.json`。
- 读取顶层 JSON 列表，逐项统计 `cot_translation_status` 的所有不同取值及各自出现次数。
- 在终端输出总记录数、具有该字段的记录数、缺少该字段的记录数，以及按状态值排序的统计结果。
- 输入文件不存在、不是合法 JSON、顶层不是列表或列表元素不是对象时，在终端报错结束。
