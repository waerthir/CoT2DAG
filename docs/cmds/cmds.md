```
python -m src.tasks.cot_to_dag.cli run --config configs/cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli status --config configs/cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config configs/cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config configs/cot_to_dag.yaml
```

---

```
python -m src.tasks.cot_to_dag.cli run --config data\cot-1\llava-cot-11b\test_cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-1\llava-cot-11b\test_cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-1\llava-cot-11b\test_cot_to_dag.yaml
```

---

```
python -m src.tasks.cot_to_dag.cli run --config data\cot-1\llava-cot-11b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-1\llava-cot-11b\cot_to_dag.yaml
```

---

```
python scripts/split_dag_nodes_relations.py `
  data\cot-1\llava-cot-11b\test_dag_2.json data\cot-1\llava-cot-11b\test_cot_2.json `
  data\cot-1\llava-cot-11b\test_node_2.json data\cot-1\llava-cot-11b\test_relationship_2.json
```

---
```
python -m src.tasks.node_evaluation.cli run `
  --config data/cot-1/llava-cot-11b/test_node_2.yaml

python -m src.tasks.node_evaluation.cli export `
  --config data/cot-1/llava-cot-11b/test_node_2.yaml

python -m src.tasks.relationship_evaluation.cli run `
  --config data/cot-1/llava-cot-11b/test_relationship_2.yaml

python -m src.tasks.relationship_evaluation.cli retry-failed `
  --config data/cot-1/llava-cot-11b/test_relationship_2.yaml

python -m src.tasks.relationship_evaluation.cli export `
  --config data/cot-1/llava-cot-11b/test_relationship_2.yaml


python -m src.tasks.node_evaluation.cli retry-failed `
  --config data/cot-1/llava-cot-11b/node.yaml

python -m src.tasks.node_evaluation.cli run `
  --config data/cot-1/llava-cot-11b/node.yaml

python -m src.tasks.node_evaluation.cli export `
  --config data/cot-1/llava-cot-11b/node.yaml


python -m src.tasks.relationship_evaluation.cli retry-failed `
  --config data/cot-1/llava-cot-11b/relationship.yaml

python -m src.tasks.relationship_evaluation.cli run `
  --config data/cot-1/llava-cot-11b/relationship.yaml

python -m src.tasks.relationship_evaluation.cli export `
  --config data/cot-1/llava-cot-11b/relationship.yaml



python -m src.tasks.node_evaluation.cli retry-failed `
  --config data/cot-1/gemini-3.1pro/node.yaml

python -m src.tasks.node_evaluation.cli run `
  --config data/cot-1/gemini-3.1pro/node.yaml

python -m src.tasks.node_evaluation.cli export `
  --config data/cot-1/gemini-3.1pro/node.yaml


python -m src.tasks.relationship_evaluation.cli retry-failed `
  --config data/cot-1/gemini-3.1pro/relationship.yaml

python -m src.tasks.relationship_evaluation.cli run `
  --config data/cot-1/gemini-3.1pro/relationship.yaml

python -m src.tasks.relationship_evaluation.cli export `
  --config data/cot-1/gemini-3.1pro/relationship.yaml
```



`data\cot-2` 下确实有七个模型目录。下面是对应的七条全采样命令；每条都会按源文件有效记录的原始顺序生成该目录下的 `cot.json`。

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\gemini-3.1-pro\gemini-3.1-pro-process1.json `
  data\cot-2\gemini-3.1-pro\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\glm-5v-turbo\glm-5v-turbo-process1.json `
  data\cot-2\glm-5v-turbo\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\gpt-5.6-sol-xhigh\gpt-5.6-sol-xhigh-process1.json `
  data\cot-2\gpt-5.6-sol-xhigh\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\grok-4.5-high\grok-4.5-high-process1.json `
  data\cot-2\grok-4.5-high\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\kimi-2.7-code\kimi-2.7-code-process1.json `
  data\cot-2\kimi-2.7-code\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\minimax-m3\minimax-m3-process1.json `
  data\cot-2\minimax-m3\cot.json `
  --all
```

```powershell
python scripts\sample_reasoning_chains.py `
  data\cot-2\qwen-3.7-plus\qwen3.7-plus-process1.json `
  data\cot-2\qwen-3.7-plus\cot.json `
  --all
```

注意最后一组的目录名和源文件名略有不同：

```text
目录：qwen-3.7-plus
文件：qwen3.7-plus-process1.json
```







七个 `data\cot-2` 目录下 `cot.json` 的检查命令如下。

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\gemini-3.1-pro\cot.json `
  --min-consecutive-han 6
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\glm-5v-turbo\cot.json `
  --min-consecutive-han 10
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\gpt-5.6-sol-xhigh\cot.json `
  --min-consecutive-han 10
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\grok-4.5-high\cot.json `
  --min-consecutive-han 10
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\kimi-2.7-code\cot.json `
  --min-consecutive-han 10
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\minimax-m3\cot.json `
  --min-consecutive-han 10
```

```powershell
python scripts\check_json_chinese.py `
  data\cot-2\qwen-3.7-plus\cot.json `
  --min-consecutive-han 10
```

如果某个文件发现中文，输出形式会类似：

```text
检测到中文：推
首次命中位置：$[0]['reasoning_chain_model']
```



```
python scripts\check_json_chinese.py `
  data\cot-2\gemini-3.1-pro\cot.json `
  --field reasoning_chain_model `
  --min-consecutive-han 1 `
  --han-ratio-threshold 5 `
  --remove-chinese `
  --filtered-output-json data\cot-2\gemini-3.1-pro\cot_without_chinese.json
```







python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\gemini-3.1-pro\gemini-3.1-pro-process1.json `
  data\cot-2\gemini-3.1-pro\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\glm-5v-turbo\glm-5v-turbo-process1.json `
  data\cot-2\glm-5v-turbo\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\gpt-5.6-sol-xhigh\gpt-5.6-sol-xhigh-process1.json `
  data\cot-2\gpt-5.6-sol-xhigh\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\grok-4.5-high\grok-4.5-high-process1.json `
  data\cot-2\grok-4.5-high\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\kimi-2.7-code\kimi-2.7-code-process1.json `
  data\cot-2\kimi-2.7-code\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\minimax-m3\minimax-m3-process1.json `
  data\cot-2\minimax-m3\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-2\qwen-3.7-plus\qwen3.7-plus-process1.json `
  data\cot-2\qwen-3.7-plus\cot.json





python -m src.tasks.cot_to_dag.cli run --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml






python -m src.tasks.cot_to_dag.cli run --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\qwen-3.7-plus\cot_to_dag.yaml