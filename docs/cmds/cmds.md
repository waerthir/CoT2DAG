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





python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-2\qwen-3.7-plus\cot_to_dag.yaml

python -m src.tasks.cot_to_dag.cli run --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-2\qwen-3.7-plus\cot_to_dag.yaml




导出cot2的dag文件

python -m src.tasks.cot_to_dag.cli export --config data\cot-2\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-2\qwen-3.7-plus\cot_to_dag.yaml





过滤cot3的仅翻译文件

python scripts\filter_translated_cot.py `
  data\cot-3\gemini-3.1-pro-process1_translated.json `
  data\cot-3\gemini-3.1-pro.json

python scripts\filter_translated_cot.py `
  data\cot-3\glm-5v-turbo-process1_translated.json `
  data\cot-3\glm-5v-turbo.json

python scripts\filter_translated_cot.py `
  data\cot-3\gpt-5.6-sol-xhigh-process1_translated.json `
  data\cot-3\gpt-5.6-sol-xhigh.json

python scripts\filter_translated_cot.py `
  data\cot-3\grok-4.5-high-process1_translated.json `
  data\cot-3\grok-4.5-high.json

python scripts\filter_translated_cot.py `
  data\cot-3\kimi-2.7-code-process1_translated.json `
  data\cot-3\kimi-2.7-code.json

python scripts\filter_translated_cot.py `
  data\cot-3\minimax-m3-process1_translated.json `
  data\cot-3\minimax-m3.json

python scripts\filter_translated_cot.py `
  data\cot-3\qwen3.7-plus-process1_translated.json `
  data\cot-3\qwen3.7-plus.json



提取cot3的所有东西，并将problem id转化为batch id

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\gemini-3.1-pro\gemini-3.1-pro.json `
  data\cot-3\gemini-3.1-pro\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\glm-5v-turbo\glm-5v-turbo.json `
  data\cot-3\glm-5v-turbo\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\gpt-5.6-sol-xhigh\gpt-5.6-sol-xhigh.json `
  data\cot-3\gpt-5.6-sol-xhigh\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\grok-4.5-high\grok-4.5-high.json `
  data\cot-3\grok-4.5-high\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\kimi-2.7-code\kimi-2.7-code.json `
  data\cot-3\kimi-2.7-code\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\minimax-m3\minimax-m3.json `
  data\cot-3\minimax-m3\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-3\qwen-3.7-plus\qwen-3.7-plus.json `
  data\cot-3\qwen-3.7-plus\cot.json





运行cot-3的所有东西

python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-3\qwen-3.7-plus\cot_to_dag.yaml

python -m src.tasks.cot_to_dag.cli run --config data\cot-3\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-3\qwen-3.7-plus\cot_to_dag.yaml

python -m src.tasks.cot_to_dag.cli export --config data\cot-3\gemini-3.1-pro\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\glm-5v-turbo\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\gpt-5.6-sol-xhigh\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\grok-4.5-high\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\kimi-2.7-code\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\minimax-m3\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-3\qwen-3.7-plus\cot_to_dag.yaml





cot4转成cot，部分

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\gemma-4-12b-it\gemma-4-12b-it-process1_translated.json `
  data\cot-4\gemma-4-12b-it\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\gemma-4-31b-it\gemma-4-31b-it-process1_translated.json `
  data\cot-4\gemma-4-31b-it\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\glm-4.1v-9b\glm-4.1v-9b-process1_translated.json `
  data\cot-4\glm-4.1v-9b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\llava-cot-11b\llava-cot-11b-process1_translated.json `
  data\cot-4\llava-cot-11b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\minicpm-v-4.5\minicpm-v-4.5-process1_translated.json `
  data\cot-4\minicpm-v-4.5\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\neo1.0-9b\neo1.0-9b-process1_translated.json `
  data\cot-4\neo1.0-9b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\nvlm-d-72b\nvlm-d-72b-process1_translated.json `
  data\cot-4\nvlm-d-72b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\qwen2.5-VL-72b\qwen2.5-vl-72b-process1_translated.json `
  data\cot-4\qwen2.5-VL-72b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\qwen3-vl-32b\qwen3-vl-32b-process1_translated.json `
  data\cot-4\qwen3-vl-32b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\qwen3-vl-8b\qwen3-vl-8b-instruct-process1_translated.json `
  data\cot-4\qwen3-vl-8b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\internvl3.5-38b\internvl3-5-38b-process1_translated.json `
  data\cot-4\internvl3.5-38b\cot.json

python scripts\extract_problem_id_reasoning_chains.py `
  data\cot-4\vl-rethinker-72b\vl-rethinker-72b-process1_translated.json `
  data\cot-4\vl-rethinker-72b\cot.json




跑cot4 部分

```powershell
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\gemma-4-12b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\gemma-4-31b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\glm-4.1v-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\llava-cot-11b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\minicpm-v-4.5\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\neo1.0-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\nvlm-d-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\qwen2.5-VL-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\qwen3-vl-32b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\qwen3-vl-8b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\internvl3.5-38b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\vl-rethinker-72b\cot_to_dag.yaml


python -m src.tasks.cot_to_dag.cli run --config data\cot-4\gemma-4-12b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\gemma-4-31b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\glm-4.1v-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\llava-cot-11b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\minicpm-v-4.5\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\neo1.0-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\nvlm-d-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\qwen2.5-VL-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\qwen3-vl-32b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\qwen3-vl-8b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\internvl3.5-38b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\vl-rethinker-72b\cot_to_dag.yaml


python -m src.tasks.cot_to_dag.cli export --config data\cot-4\gemma-4-12b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\gemma-4-31b-it\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\glm-4.1v-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\llava-cot-11b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\minicpm-v-4.5\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\neo1.0-9b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\nvlm-d-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\qwen2.5-VL-72b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\qwen3-vl-32b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\qwen3-vl-8b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\internvl3.5-38b\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli export --config data\cot-4\vl-rethinker-72b\cot_to_dag.yaml
```




python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\minicpm-v-4.5\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli retry-failed --config data\cot-4\nvlm-d-72b\cot_to_dag.yaml



python -m src.tasks.cot_to_dag.cli run --config data\cot-4\minicpm-v-4.5\cot_to_dag.yaml
python -m src.tasks.cot_to_dag.cli run --config data\cot-4\nvlm-d-72b\cot_to_dag.yaml




独立化cot 的 batch id

python scripts\make_batch_ids_unique.py `
  data\cot-4\internvl3.5-38b\cot.json `
  data\cot-4\internvl3.5-38b\cot_unique.json