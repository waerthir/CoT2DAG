# DAG 节点与关系拆分脚本：实施计划

## 目标

新增 `scripts/split_dag_nodes_relations.py`。输入 DAG 文件和 CoT 源文件，输出节点 JSON 与关系 JSON，供后续评分使用。

输入 DAG 文件：

```json
[
  {
    "batch_id": "001",
    "graph": {"graph_logic": {}}
  }
]
```

输入 CoT 源文件：

```json
[
  {
    "batch_id": "001",
    "reasoning_chain_model": "..."
  }
]
```

两个输入文件以 `batch_id` 一一对应；脚本直接按该约定关联，不添加跨文件 ID 补偿或冗余匹配逻辑。

## 命令行

```bash
python scripts/split_dag_nodes_relations.py \
  <dag_input_json> <cot_input_json> \
  <nodes_output_json> <relations_output_json>
```

四个路径均由命令行传入。相对路径以项目根目录为基准解析；脚本从自身位置定位项目根目录。

## 节点 JSON

遍历每张图的 `conditions`、`intermediate_steps`、`final_conclusion`，按此顺序输出：

```json
[
  {
    "batch_id": "001-C_1",
    "reasoning_chain_model": "完整 CoT",
    "content": "节点内容"
  }
]
```

节点 ID：

```python
node_batch_id = f"{graph_batch_id}-{node_id}"
```

节点记录字段固定为 `batch_id`、`reasoning_chain_model`、`content`。

## 关系 JSON

关系 JSON 的记录只以 I/O 节点为子节点：`intermediate_steps` 的每个节点及 `final_conclusion` 各生成一个关系单元。C 节点不独立生成关系记录。

```json
[
  {
    "batch_id": "001-I_2",
    "reasoning_chain_model": "完整 CoT",
    "content": "子节点内容",
    "parents": [
      {
        "batch_id": "001-C_1",
        "content": "父节点内容"
      },
      {
        "batch_id": "001-I_1",
        "content": "父节点内容"
      }
    ],
    "reasoning_logic": "...",
    "type": "逻辑推导"
  }
]
```

关系单元 ID：

```python
relation_batch_id = f"{graph_batch_id}-{child_node_id}"
```

关系单元的 `batch_id` 与对应子节点在节点 JSON 中的 `batch_id` 相同。父节点使用完整节点 `batch_id`，可直接关联节点 JSON。

若 I/O 子节点的实际父节点包含 C 节点，则该 C 节点保留在该关系单元的 `parents` 中，作为该推理关系的输入上下文；它不构成独立的 C 层关系记录。

## 实现

1. 使用 `argparse` 解析四个路径；拒绝任意两个路径相同。
2. 从 `Path(__file__)` 定位项目根目录并解析相对路径。
3. 读取 CoT 源文件，建立 `batch_id -> reasoning_chain_model` 映射。
4. 读取 DAG 文件；验证图记录、`graph.graph_logic`、图内节点 ID 唯一性和父节点引用。
5. 对每张图按其 `batch_id` 从 CoT 映射取得完整推理链，建立 `node_id -> node` 查找表。
6. 按图顺序及图内节点顺序生成节点记录和关系单元。
7. 创建输出父目录；两个输出均先写临时文件，再原子替换目标文件。
8. 打印图数量、节点数量、关系单元数量及输出路径。

## 验收

- 节点记录字段恰为 `batch_id`、`reasoning_chain_model`、`content`；
- 关系记录字段恰为 `batch_id`、`reasoning_chain_model`、`content`、`parents`、`reasoning_logic`、`type`；
- 节点和关系记录的 `batch_id` 都为 `{图 batch_id}-{节点 id}`；
- 每个 I/O 子节点生成一个关系单元，C 节点不独立生成关系单元；
- I/O 子节点的 `parents` 保留其全部实际父节点，包括作为推理输入的 C 节点；
- 关系父节点使用完整节点 `batch_id` 与节点 JSON 关联；
- 节点和关系单元顺序稳定；
- 路径冲突、DAG 结构错误、重复节点 ID 或缺失父节点时终止并报告错误。
