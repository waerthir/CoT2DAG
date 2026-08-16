"""合并两位人工标注与机器大表，为第三人裁决生成工作清单。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ClaimKey = tuple[str, str]


class ClaimJudgmentMergeError(ValueError):
    """输入判断表不能安全合并时抛出。"""


@dataclass(frozen=True)
class JudgmentTable:
    """一份节点二值判断表及其按输入顺序保存的结构。"""

    labels: dict[ClaimKey, bool]
    ordered_records: list[tuple[str, list[str]]]


def build_parser() -> argparse.ArgumentParser:
    """构造四个位置参数的命令行解析器。"""

    parser = argparse.ArgumentParser(description="合并人工 A/B 标注与机器节点判断")
    parser.add_argument("annotator_a_json", type=Path, help="人工标注者 A 的节点判断 JSON")
    parser.add_argument("annotator_b_json", type=Path, help="人工标注者 B 的节点判断 JSON")
    parser.add_argument("machine_judge_json", type=Path, help="可含额外记录的机器判断大表 JSON")
    parser.add_argument("output_json", type=Path, help="第三人裁决工作清单输出路径")
    return parser


def _load_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    """读取顶层对象列表 JSON。"""

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClaimJudgmentMergeError(f"{description}不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ClaimJudgmentMergeError(f"{description}不是合法 JSON：{path}；{exc}") from exc
    if not isinstance(raw_data, list):
        raise ClaimJudgmentMergeError(f"{description}顶层必须是列表。")
    if not all(isinstance(record, dict) for record in raw_data):
        raise ClaimJudgmentMergeError(f"{description}顶层列表中的每项必须是对象。")
    return raw_data


def load_judgment_table(path: Path, description: str) -> JudgmentTable:
    """读取图级节点判断 JSON，并检查 batch/node 键的唯一性。"""

    labels: dict[ClaimKey, bool] = {}
    ordered_records: list[tuple[str, list[str]]] = []
    seen_batch_ids: set[str] = set()
    for record_index, record in enumerate(_load_json_list(path, description)):
        source = f"{description}第 {record_index} 条"
        batch_id = record.get("batch_id")
        if not isinstance(batch_id, str) or not batch_id:
            raise ClaimJudgmentMergeError(f"{source}的 batch_id 必须是非空字符串。")
        if batch_id in seen_batch_ids:
            raise ClaimJudgmentMergeError(f"{description}中存在重复 batch_id：{batch_id}")
        seen_batch_ids.add(batch_id)

        node_evaluations = record.get("node_evaluations")
        if not isinstance(node_evaluations, list):
            raise ClaimJudgmentMergeError(f"{source}的 node_evaluations 必须是列表。")
        node_ids: list[str] = []
        seen_node_ids: set[str] = set()
        for node_index, node in enumerate(node_evaluations):
            node_source = f"{source}的节点 {node_index}"
            if not isinstance(node, dict):
                raise ClaimJudgmentMergeError(f"{node_source}必须是对象。")
            node_id = node.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                raise ClaimJudgmentMergeError(f"{node_source}的 node_id 必须是非空字符串。")
            if node_id in seen_node_ids:
                raise ClaimJudgmentMergeError(
                    f"{description}中 batch_id={batch_id} 存在重复 node_id：{node_id}"
                )
            is_correct = node.get("is_correct")
            if not isinstance(is_correct, bool):
                raise ClaimJudgmentMergeError(f"{node_source}的 is_correct 必须是布尔值。")
            seen_node_ids.add(node_id)
            node_ids.append(node_id)
            labels[(batch_id, node_id)] = is_correct
        ordered_records.append((batch_id, node_ids))
    return JudgmentTable(labels=labels, ordered_records=ordered_records)


def _format_keys(keys: set[ClaimKey]) -> str:
    """将 claim 键集合格式化为稳定的错误报告。"""

    return "\n".join(f"- batch_id={batch_id}, node_id={node_id}" for batch_id, node_id in sorted(keys))


def require_same_human_keys(annotator_a: JudgmentTable, annotator_b: JudgmentTable) -> None:
    """确认两位人工标注者覆盖完全相同的 claim 集合。"""

    a_keys = set(annotator_a.labels)
    b_keys = set(annotator_b.labels)
    missing_from_b = a_keys - b_keys
    extra_in_b = b_keys - a_keys
    if missing_from_b or extra_in_b:
        details: list[str] = []
        if missing_from_b:
            details.append(
                f"人工 B 缺少 {len(missing_from_b)} 个 A 的节点：\n{_format_keys(missing_from_b)}"
            )
        if extra_in_b:
            details.append(
                f"人工 B 多出 {len(extra_in_b)} 个节点：\n{_format_keys(extra_in_b)}"
            )
        raise ClaimJudgmentMergeError("人工 A/B 节点集合不一致：\n" + "\n".join(details))


def require_machine_labels(
    human_keys: set[ClaimKey], machine: JudgmentTable
) -> None:
    """确认机器大表含有全部 A/B 所需节点。"""

    missing_machine_keys = human_keys - set(machine.labels)
    if missing_machine_keys:
        raise ClaimJudgmentMergeError(
            f"机器判断大表缺少 {len(missing_machine_keys)} 个 A/B 所需节点：\n"
            f"{_format_keys(missing_machine_keys)}"
        )


def build_output(
    annotator_a: JudgmentTable,
    annotator_b: JudgmentTable,
    machine: JudgmentTable,
    annotator_a_path: Path,
    annotator_b_path: Path,
    machine_path: Path,
) -> dict[str, Any]:
    """按人工 A 的图与节点顺序构造第三人裁决工作清单。"""

    human_keys = set(annotator_a.labels)
    records: list[dict[str, Any]] = []
    agreement_count = 0
    disagreement_count = 0
    for batch_id, node_ids in annotator_a.ordered_records:
        merged_nodes: list[dict[str, Any]] = []
        for node_id in node_ids:
            key = (batch_id, node_id)
            a_label = annotator_a.labels[key]
            b_label = annotator_b.labels[key]
            requires_third_annotator = a_label != b_label
            if requires_third_annotator:
                disagreement_count += 1
            else:
                agreement_count += 1
            merged_nodes.append(
                {
                    "node_id": node_id,
                    "annotator_a_is_correct": a_label,
                    "annotator_b_is_correct": b_label,
                    "machine_is_correct": machine.labels[key],
                    "requires_third_annotator": requires_third_annotator,
                    "third_annotator_is_correct": None,
                }
            )
        records.append({"batch_id": batch_id, "node_evaluations": merged_nodes})

    return {
        "inputs": {
            "annotator_a_json": str(annotator_a_path),
            "annotator_b_json": str(annotator_b_path),
            "machine_judge_json": str(machine_path),
        },
        "summary": {
            "total_node_count": len(human_keys),
            "annotator_agreement_count": agreement_count,
            "annotator_disagreement_count": disagreement_count,
            "pending_third_adjudication_count": disagreement_count,
            "machine_table_total_node_count": len(machine.labels),
            "machine_table_unreferenced_node_count": len(machine.labels) - len(human_keys),
        },
        "records": records,
    }


def write_json(output_path: Path, output: dict[str, Any]) -> None:
    """通过临时文件原子写入合并后的裁决工作清单。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)


def main() -> int:
    """执行严格的 A/B 对齐、机器查找与裁决清单输出。"""

    args = build_parser().parse_args()
    try:
        annotator_a = load_judgment_table(args.annotator_a_json, "人工标注者 A 文件")
        annotator_b = load_judgment_table(args.annotator_b_json, "人工标注者 B 文件")
        machine = load_judgment_table(args.machine_judge_json, "机器判断大表")
        require_same_human_keys(annotator_a, annotator_b)
        require_machine_labels(set(annotator_a.labels), machine)
        output = build_output(
            annotator_a,
            annotator_b,
            machine,
            args.annotator_a_json,
            args.annotator_b_json,
            args.machine_judge_json,
        )
        write_json(args.output_json, output)
    except ClaimJudgmentMergeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    summary = output["summary"]
    print(
        f"已合并节点={summary['total_node_count']}，"
        f"A/B 一致={summary['annotator_agreement_count']}，"
        f"待第三人裁决={summary['pending_third_adjudication_count']}，"
        f"机器表未引用节点={summary['machine_table_unreferenced_node_count']}："
        f"{args.output_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
