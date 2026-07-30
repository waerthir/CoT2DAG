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


python -m src.tasks.relationship_evaluation.cli run `
  --config data/cot-1/llava-cot-11b/relationship.yaml
```