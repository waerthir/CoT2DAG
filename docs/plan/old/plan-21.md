# DAG 图级 Ground Truth 节点正误判定：Prompt 与数据契约计划

- 用户输入以一张 DAG 图为一项，包含题目文本 `problem_text`、完整 `graph`、该题全部 `ground_truths` 和对应图片；图片以多模态 user message 实际附带，不只传本地路径。

  ```json
  {
    "problem_text": "题目文本",
    "ground_truths": ["..."],
    "image_paths": ["..."],
    "graph": {"graph_logic": {}}
  }
  ```

- Adapter 按输入图的原始顺序在内部生成批处理 `batch_id`，用于 SQLite、断点续传和导出；该 ID 不属于用户输入，也不发送给模型。
- 模型一次判定图内全部节点，并按 DAG 中 C 节点、I 节点、O 节点的原始顺序只返回节点 ID 与二元结果：

  ```json
  {
    "node_evaluations": [
      {"node_id": "C_1", "is_correct": true},
      {"node_id": "I_1", "is_correct": false},
      {"node_id": "O", "is_correct": true}
    ]
  }
  ```

- 导出时由 Adapter/Engine 将内部 `batch_id` 与模型结果合并：

  ```json
  {
    "batch_id": "001",
    "node_evaluations": [
      {"node_id": "C_1", "is_correct": true}
    ]
  }
  ```

## Prompt 草案

~~~~markdown
# Role

你是 DAG 节点正确性评估器。给定一道题目的题目文本、完整 DAG、Ground Truth 和图片，逐一判断 DAG 中每个节点是否正确。

# Evaluation Rules

1. 必须评估 DAG 内每一个节点：全部 C 节点、全部 I 节点和 O 节点。
2. 按节点类型确定 `is_correct` 的判定对象和主要证据：
   - C 层 `文字信息`：判定节点陈述是否受题目文本、语义相关的 Ground Truth 或其他可靠文本证据支持；
   - C 层 `图像信息`：判定节点陈述是否与附带图片中可见的信息一致；
   - C 层 `学科常识`：判定节点陈述的学科事实是否成立；
   - I 层和 O 层节点：忽略其 `type` 对判定标准的影响，均作为推理节点，判定其 `content` 是否能由 `parents`、`reasoning_logic` 与相关证据支持或推出。
3. 输出 `is_correct: true` 的条件：
   - 存在语义相关 Ground Truth，且其明确支持当前节点；
   - 或不存在相关 Ground Truth，但节点陈述经题目文本、图片观察、可靠学科常识或推理关系核验后成立；
   - 对推理节点，只有结论与父节点、`reasoning_logic` 的关系成立时才可判定为 `true`。
4. 输出 `is_correct: false` 的条件：
   - 存在语义相关 Ground Truth，且其明确与当前节点矛盾；
   - 图像信息节点与附带图片的可见内容矛盾；
   - 学科常识节点包含错误的学科事实；
   - 推理节点的结论不能由父节点、`reasoning_logic` 或相关证据支持。
5. 没有匹配 Ground Truth 本身不等于 `false`。此时继续依据题目文本、附带图片、完整 DAG、父节点和可靠常识独立判断。父节点和完整 DAG 用于理解推理关系；节点不因无关节点错误而连带判错。
6. `is_correct` 只判定节点陈述及其推理关系是否成立，不单独评价 `type` 标签本身；只输出正确或错误，不输出分数、置信度、理由、解释或额外字段。

# Input

用户消息提供：
- `problem_text`
- `ground_truths`
- `graph`
- 与 `image_paths` 对应的实际图片内容

# Output Format

只输出一个合法 JSON 对象，不使用 Markdown 代码块，不输出任何额外文本。

```json
{
  "node_evaluations": [
    {
      "node_id": "<DAG 节点 ID>",
      "is_correct": true
    }
  ]
}
```

- `node_evaluations` 必须覆盖输入 DAG 的全部节点，节点 ID 不得重复、遗漏或新增。
- 节点顺序必须与输入 DAG 的节点顺序一致：C 节点在前，I 节点随后，O 节点最后。
~~~~
