# 推理链随机抽样脚本：实施计划

## 目标

新增 `scripts/sample_reasoning_chains.py`。从输入 JSON 数组随机抽取指定数量的元素，输出只包含 `batch_id` 和 `reasoning_chain_model` 的 JSON 数组。

## 命令行接口

```bash
python scripts/sample_reasoning_chains.py \
  <input_json> <output_json> \
  --count <N> \
  [--seed <integer>]
```

参数：

- `input_json`：源 JSON 文件路径；
- `output_json`：抽样结果文件路径；
- `--count`：请求抽取数量，要求为非负整数；
- `--seed`：可选随机种子；提供后，相同输入和参数得到相同抽样结果。

使用命令行参数，不新增 YAML 配置。

## 输入与输出

输入必须为 JSON 数组；每个元素必须是对象，且包含非空字符串字段：

```json
{
  "reasoning_chain_model": "..."
}
```

输出格式：

```json
[
  {
    "batch_id": "001",
    "reasoning_chain_model": "..."
  }
]
```

源元素的其他字段不写入输出。

## 抽样与编号规则

```python
actual_count = min(requested_count, len(source_items))
sampled_items = rng.sample(source_items, actual_count)
width = len(str(requested_count))
```

对 `sampled_items` 的返回顺序从 1 开始编号：

```python
batch_id = f"{index:0{width}d}"
```

示例：

| `--count` | 源文件可用条数 | 实际输出数 | `batch_id` |
| --- | ---: | ---: | --- |
| `3` | 100 | 3 | `1`、`2`、`3` |
| `20` | 100 | 20 | `01` 至 `20` |
| `100` | 3 | 3 | `001`、`002`、`003` |

编号宽度由用户请求的 `--count` 决定；当源文件不足时，仍保留本次请求对应的编号格式。

## 实现步骤

1. 使用 `argparse` 解析路径、`--count` 与可选 `--seed`。
2. 检查输入路径存在、输入输出路径不同、`--count >= 0`。
3. 使用 UTF-8 读取 JSON，验证顶层数组和每个元素的 `reasoning_chain_model`。
4. 创建 `random.Random(seed)`；未提供种子时创建无种子的随机生成器。
5. 按 `actual_count` 使用 `rng.sample` 进行无放回随机抽样。
6. 按规则构造输出数组，仅写入 `batch_id` 与 `reasoning_chain_model`。
7. 创建输出父目录；先写临时文件，再原子替换目标文件。
8. 在终端打印请求数量、源数量、实际抽取数量、输出路径和种子信息。

## 验收

- 输出元素数为 `min(--count, 输入数组长度)`；
- 每个输出元素只有 `batch_id` 与 `reasoning_chain_model`；
- `batch_id` 连续、唯一，宽度符合请求数量；
- 提供相同 `--seed` 时抽样结果一致；
- 不提供 `--seed` 时每次运行按随机状态抽样；
- 输入格式错误、缺失推理链字段、负数数量或输入输出同路径时给出清晰错误并终止。
