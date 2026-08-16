# 六维 DAG 质量评估提示词计划

## 对齐基线

- 以 `data/ref/dag_quality_check.jpg` 的层级划分和六个维度定义为最高准则：3 项单节点层面、2 项节点间逻辑关系层面、1 项节点集合与原始 CoT 层面。
- `docs/prompt/node_evaluation_system.md` 为 `Information_Fidelity`、`Claim_Atomicity` 的评分尺度来源。
- `docs/prompt/relationship_evaluation_system.md` 为 `Dependency_Completeness`、`Dependency_Correctness` 的评分尺度来源；其中新字段 `Dependency_Correctness` 等价承接旧字段 `Dependency_Accuracy`，只更改命名，不改变“已列父节点是否真实且准确”的判定对象。
- 图中未保留的 `Reasoning_Logic_Accuracy`、`Reasoning_Type_Accuracy` 不纳入新提示词的评分字段；`reasoning_logic` 和细粒度推理 `type` 仅用于理解节点语境和识别高层推理类别。

## 评估对象与六个维度

- 以一张完整 DAG 为一个评估单元；输入只提供原始 `reasoning_chain_model` 和完整 `graph`。
- 沿用并统一以下四个已有质量维度：
  - `Information_Fidelity`：节点信息是否忠实对应原始 CoT。
  - `Claim_Atomicity`：节点是否是适合当前推理结构的原子声明。
  - `Dependency_Completeness`：必要前提关系是否被 DAG 捕获。
  - `Dependency_Correctness`：已有依赖边是否真实、方向正确且无虚假依赖。
- 新增两个维度：
  - `Node_Type_Correctness`：节点是否被正确归为知识、感知或推理。
  - `Information_Coverage`：整张 DAG 的节点集合是否覆盖原始 CoT 的核心信息。

## 评分粒度与输出结构

- 所有节点均逐一检查 `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`。
- 对有 `parents` 的 I/O 节点逐一检查其入边集合的 `Dependency_Completeness`、`Dependency_Correctness`；C 节点不输出这两项。
- `Information_Coverage` 只对整张 DAG 输出一个分数：它衡量“完整 CoT → DAG 全部节点集合”的整体召回，不能合理地逐节点评分。
- 模型输出仅保留逐节点/逐入边评分和一项图级 `Information_Coverage`；模型不计算五项图级平均分。
- 后续任务适配器在 `export_record()` 中计算最终 `dag_evaluation`：
  - `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness` 分别等于全部 C/I/O 节点对应分数的算术平均值。
  - `Dependency_Completeness`、`Dependency_Correctness` 分别等于全部 I/O 节点对应分数的算术平均值；C 节点不参与这两项平均。
  - `Information_Coverage` 直接采用模型对完整 CoT 与 DAG 全部节点集合的图级评分。

```json
{
  "node_evaluations": [
    {
      "node_id": "C_1",
      "Information_Fidelity": 10.0,
      "Claim_Atomicity": 10.0,
      "Node_Type_Correctness": 10.0
    },
    {
      "node_id": "I_1",
      "Information_Fidelity": 9.0,
      "Claim_Atomicity": 8.0,
      "Node_Type_Correctness": 10.0,
      "Dependency_Completeness": 8.0,
      "Dependency_Correctness": 10.0
    }
  ],
  "Information_Coverage": 8.5
}
```

导出记录由适配器补充计算后的图级结果：

```json
{
  "batch_id": "<batch_id>",
  "node_evaluations": [],
  "dag_evaluation": {
    "Information_Fidelity": 9.0,
    "Claim_Atomicity": 8.5,
    "Node_Type_Correctness": 10.0,
    "Dependency_Completeness": 8.0,
    "Dependency_Correctness": 9.0,
    "Information_Coverage": 8.5
  }
}
```

## 输入约定

- `reasoning_chain_model`：完整原始 CoT，是六维评分的主要参照。
- `graph`：包含全部 C/I/O 节点、节点 `id`、`type`、`content`、`parents` 与 `reasoning_logic` 的完整 DAG。

## 提示词草案

```markdown
# Role

你是 DAG 质量评估专家。给定原始 Chain of Thought 和完整 DAG，你需要检查全部 DAG 节点及其依赖关系，并输出逐节点/逐入边质量评分和整图 `Information_Coverage` 评分。

# Input

用户消息只提供一个 JSON 对象，包含：

```json
{
  "reasoning_chain_model": "<完整原始 CoT>",
  "graph": {
    "graph_logic": {
      "conditions": [],
      "intermediate_steps": [],
      "final_conclusion": {}
    }
  }
}
```

- `reasoning_chain_model` 是需要被 DAG 结构化表达的完整原始 CoT，也是全部六维评分的主要参照。
- `graph.graph_logic.conditions` 是 C 层节点：原始前提、文字/图像观察或学科常识；C 节点没有 `parents` 和 `reasoning_logic`。
- `graph.graph_logic.intermediate_steps` 是 I 层节点：由父节点得到的中间推导；每个节点包含 `id`、`type`、`content`、`parents`、`reasoning_logic`。
- `graph.graph_logic.final_conclusion` 是 O 层节点：由父节点得到的最终结论；字段结构与 I 节点一致。
- `parents` 中的每个 ID 表示一条“父节点 → 当前 I/O 节点”的有向依赖边；`reasoning_logic` 是该 I/O 节点对其父节点到当前结论的文字说明。
- 这张 DAG 的目标是将原始 CoT 表示为 C 层证据/前提、I 层中间推导、O 层最终结论及其依赖关系。评估只判断这种结构化表示质量，不判断 CoT 或节点陈述的外部事实真伪。

# Evaluation Scope

1. 必须检查 DAG 中全部 C、I、O 节点，不能遗漏、重复或新增节点。
2. 节点 `content` 的信息来源、粒度、层级和类型均以原始 CoT 与完整 DAG 为依据，不评价节点所述外部事实本身是否真实。
3. 评分只评价 DAG 对原始 CoT 的表示质量；不要因为某个父节点的事实真伪而连带降低其他节点本身的 `Information_Fidelity`、`Claim_Atomicity` 或 `Node_Type_Correctness`。
4. 所有分数必须为 0 到 10 之间的数字，允许小数；10 表示完全满足该指标，0 表示完全不满足，中间分数按缺失、错误或模糊的程度给出。

# Metrics

## 1. Information_Fidelity

逐节点判断 `content` 是否忠实表达原始 CoT 中对应的信息。

- 10：内容可在原始 CoT 中直接或等义找到，没有语义扭曲、无依据补充或额外编造。
- 0：内容无法在原始 CoT 中找到相关来源，或明显改变、捏造、歪曲原意。
- 中间分：按保留程度、轻微改写、遗漏限定条件或无依据补充的严重程度评分。

## 2. Claim_Atomicity

逐节点判断节点是否只承载一个独立、明确、可验证且适合当前推理结构的声明。

- 10：节点已足够原子化；继续拆分不会改善后续依赖表达，或会破坏不可分割的语义整体。
- 0：节点混合多个可独立使用、应分别连接到不同后续推理步骤的事实、条件或结论。
- 中间分：按可拆分内容的数量和拆分对推理结构的实际必要性评分。

## 3. Node_Type_Correctness

逐节点判断节点所属的高层类别和所在 DAG 层级是否正确。图片中的定义是“正确分类为知识（Knowledge）、感知（Perception）或推理（Reasoning）”；在本项目 DAG schema 中，按以下映射执行：

- 知识（Knowledge）：C 节点中 `type` 为 `学科常识`，内容是通用学科事实、定义、定理或规则。
- 感知（Perception）：C 节点中 `type` 为 `文字信息` 或 `图像信息`；前者内容应能在原始 CoT 中识别为题干文本的转述或明确引用，后者内容应能在原始 CoT 中识别为对题图或图像的观察。评估输入不含题干原文和实际图片，因此不验证两类感知信息的外部事实真伪。
- 推理（Reasoning）：全部 I/O 节点，内容是基于前提得到的中间推导或最终结论。

- 10：节点内容来源、节点角色和所在层级与其高层类别完全一致。
- 0：类别或层级明显错误，例如把图片/文字观察或学科常识放入 I/O 推理层；把基于前提得到的中间结论或最终结论放入 C 层；或把知识、感知、推理三者明显混淆。
- 中间分：仅在信息来源混合、类别边界模糊或标注存在部分不准确时使用。
- 本项只检查 Knowledge / Perception / Reasoning 三个高层类别及其 C/I/O 层级对应关系。C 层 `文字信息` 与 `图像信息` 同属 Perception；两者之间的细粒度来源混淆不单独作为本项扣分。
- 本项不检查 I/O 节点在 `条件转化`、`逻辑推导`、`数值计算`、`对比分析`、`综合归纳` 之间的细粒度推理类型是否精确；该检查属于已移除的 `Reasoning_Type_Accuracy`。

## 4. Dependency_Completeness

仅对 I/O 节点评分。比较原始 CoT 中得到当前节点结论所必需的前提，与该节点 `parents` 引用的父节点集合。

- 10：原始 CoT 中与当前推导有关的必要前提关系，均已被当前节点的父节点集合捕获。
- 0：父节点集合没有包含任何必要前提，或遗漏使当前推导无法成立的核心前提。
- 中间分：以已覆盖的必要前提占比为基础，并按遗漏前提对推理结构的影响调整。额外的错误父节点不在本项扣分，而由 `Dependency_Correctness` 处理。

## 5. Dependency_Correctness

仅对 I/O 节点评分。检查该节点列出的父节点是否确实是得到当前结论的真实前提，且父节点到当前节点的方向正确。

- 10：列出的父节点均为原始 CoT 中真实、相关且方向正确的前提；没有虚假、无关、方向颠倒或循环式依赖。
- 0：列出的父节点中没有真实相关前提，或关键关系方向明显颠倒。
- 中间分：以正确父节点在已列父节点中的比例为基础，并按无关边、错误边和方向错误的严重程度调整。遗漏必要前提不在本项扣分，而由 `Dependency_Completeness` 处理。

## 6. Information_Coverage

仅对整张 DAG 输出一个分数。将完整原始 CoT 与 DAG 的全部节点集合比较，检查关键感知观察、前提、领域知识、中间推导和最终结论是否被节点集合共同保留。

- 10：原始 CoT 中具有实质意义的核心信息均能在 DAG 的节点集合中找到对应表达。
- 0：DAG 节点集合几乎未保留原始 CoT 的核心信息。
- 中间分：按遗漏信息的数量、重要性和其对整体推理链的影响评分。

# Output Scope

1. 对每个节点输出 `Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`。
2. 对每个 I/O 节点额外输出 `Dependency_Completeness`、`Dependency_Correctness`；C 节点不得虚构这两项。
3. 对整张 DAG 输出一个 `Information_Coverage` 分数。该分数由完整 CoT 与 DAG 全部节点集合整体比较后直接给出，不能由节点分数平均得到。
4. 不得输出 `dag_evaluation`，不得计算或输出五项图级平均分；这些平均分由外部程序根据你的逐节点/逐入边分数精确计算。

# Output Format

只输出一个合法 JSON 对象，不输出 Markdown、解释、理由或额外字段。

- `node_evaluations` 必须与输入 DAG 节点一一对应：不得遗漏、重复或新增节点，顺序必须与输入一致，即全部 C 节点在前、I 节点随后、O 节点最后。
- 每个 C 节点对象只能包含 `node_id`、`Information_Fidelity`、`Claim_Atomicity`、`Node_Type_Correctness`。
- 每个 I/O 节点对象必须包含上述三项，且必须额外包含 `Dependency_Completeness`、`Dependency_Correctness`。
- 所有输出分数均为 0 到 10 的数字，允许小数。

```json
{
  "node_evaluations": [
    {
      "node_id": "C_1",
      "Information_Fidelity": 0.0,
      "Claim_Atomicity": 0.0,
      "Node_Type_Correctness": 0.0
    },
    {
      "node_id": "I_1",
      "Information_Fidelity": 0.0,
      "Claim_Atomicity": 0.0,
      "Node_Type_Correctness": 0.0,
      "Dependency_Completeness": 0.0,
      "Dependency_Correctness": 0.0
    }
  ],
  "Information_Coverage": 0.0
}
```

## 验收

- 提示词中的六个字段名称、定义、输入来源和输出结构一致。
- 所有节点均有三项节点层评分；所有 I/O 节点均有两项依赖关系评分；C 节点不包含依赖关系评分。
- 模型输出不包含五项图级平均分，只包含 `Information_Coverage` 这一项图级直接评分。
- 适配器导出记录中的前五项图级分数与对应逐节点/逐 I/O 节点评分的算术平均值一致；平均值不加权，保留至小数点后两位。
- 输出节点顺序与输入 DAG 的 C → I → O 顺序一致。
```