# 已翻译 CoT 筛选计划

- 新建 `scripts/filter_translated_cot.py`，使用两个命令行位置参数指定输入 JSON 路径与输出 JSON 路径。
- 读取顶层为列表的输入 JSON，按原始顺序保留 `cot_translation_status` 严格等于 `translated` 的完整元素。
- 将保留结果写为 JSON 列表；不改写元素内部字段。
- 在终端输出输入总数、保留数量和输出路径。
- 输入文件不存在、不是合法 JSON、顶层不是列表、列表元素不是对象，或输出路径与输入路径相同时，在终端报错结束。
