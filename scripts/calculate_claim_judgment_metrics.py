"""计算人工验证的节点级正确率与一致性指标。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ClaimKey = tuple[str, str]


class ClaimJudgmentMetricsError(ValueError):
    """输入的人工裁决工作清单无法安全统计时抛出。"""


@dataclass(frozen=True)
class ClaimLabels:
    """单个节点用于统计的 A/B、机器与最终人工标签。"""

    annotator_a: bool
    annotator_b: bool
    machine: bool
    final_human: bool
    requires_third_annotator: bool


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数。"""

    parser = argparse.ArgumentParser(
        description="计算人工验证的 Claim Correct Rate 与 Judgment Agreement"
    )
    parser.add_argument(
        "input_json",
        type=Path,
        help="已完成第三人裁决的 dag_evaluation_50_sample_human.json 路径",
    )
    return parser


def load_claim_labels(input_path: Path) -> tuple[dict[ClaimKey, ClaimLabels], int]:
    """读取并校验工作清单，返回节点标签映射与图记录数。"""

    try:
        raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClaimJudgmentMetricsError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ClaimJudgmentMetricsError(f"输入文件不是合法 JSON：{input_path}；{exc}") from exc

    if not isinstance(raw_data, dict):
        raise ClaimJudgmentMetricsError("输入 JSON 顶层必须是对象。")
    records = raw_data.get("records")
    if not isinstance(records, list):
        raise ClaimJudgmentMetricsError("输入 JSON 缺少 records 列表。")

    labels: dict[ClaimKey, ClaimLabels] = {}
    seen_batch_ids: set[str] = set()
    for record_index, record in enumerate(records):
        source = f"records[{record_index}]"
        if not isinstance(record, dict):
            raise ClaimJudgmentMetricsError(f"{source} 必须是对象。")
        batch_id = record.get("batch_id")
        if not isinstance(batch_id, str) or not batch_id:
            raise ClaimJudgmentMetricsError(f"{source}.batch_id 必须是非空字符串。")
        if batch_id in seen_batch_ids:
            raise ClaimJudgmentMetricsError(f"存在重复 batch_id：{batch_id}")
        seen_batch_ids.add(batch_id)

        node_evaluations = record.get("node_evaluations")
        if not isinstance(node_evaluations, list):
            raise ClaimJudgmentMetricsError(f"{source}.node_evaluations 必须是列表。")
        seen_node_ids: set[str] = set()
        for node_index, node in enumerate(node_evaluations):
            node_source = f"{source}.node_evaluations[{node_index}]"
            if not isinstance(node, dict):
                raise ClaimJudgmentMetricsError(f"{node_source} 必须是对象。")
            node_id = node.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                raise ClaimJudgmentMetricsError(f"{node_source}.node_id 必须是非空字符串。")
            if node_id in seen_node_ids:
                raise ClaimJudgmentMetricsError(
                    f"batch_id={batch_id} 存在重复 node_id：{node_id}"
                )
            seen_node_ids.add(node_id)

            annotator_a = node.get("annotator_a_is_correct")
            annotator_b = node.get("annotator_b_is_correct")
            machine = node.get("machine_is_correct")
            requires_third = node.get("requires_third_annotator")
            third = node.get("third_annotator_is_correct")
            for field_name, value in (
                ("annotator_a_is_correct", annotator_a),
                ("annotator_b_is_correct", annotator_b),
                ("machine_is_correct", machine),
                ("requires_third_annotator", requires_third),
            ):
                if not isinstance(value, bool):
                    raise ClaimJudgmentMetricsError(
                        f"{node_source}.{field_name} 必须是布尔值。"
                    )

            if requires_third:
                if not isinstance(third, bool):
                    raise ClaimJudgmentMetricsError(
                        f"{node_source} 需要第三人裁决，但 third_annotator_is_correct "
                        "不是布尔值。"
                    )
                final_human = third
            else:
                if annotator_a != annotator_b:
                    raise ClaimJudgmentMetricsError(
                        f"{node_source} 标记为无需第三人裁决，但 A/B 标签不一致。"
                    )
                final_human = annotator_a

            key = (batch_id, node_id)
            if key in labels:
                raise ClaimJudgmentMetricsError(
                    f"存在重复 claim 键：batch_id={batch_id}, node_id={node_id}"
                )
            labels[key] = ClaimLabels(
                annotator_a=annotator_a,
                annotator_b=annotator_b,
                machine=machine,
                final_human=final_human,
                requires_third_annotator=requires_third,
            )
    if not labels:
        raise ClaimJudgmentMetricsError("records 中不包含可统计的 claim。")
    return labels, len(records)


def safe_percentage(numerator: int, denominator: int) -> float:
    """将比例稳定地转换为百分比。"""

    return numerator / denominator * 100.0


def cohens_kappa(labels: list[ClaimLabels]) -> float | None:
    """计算 A/B 二元标签的 Cohen's kappa；不可定义时返回 None。"""

    total = len(labels)
    observed_agreement = sum(
        item.annotator_a == item.annotator_b for item in labels
    ) / total
    a_true_rate = sum(item.annotator_a for item in labels) / total
    b_true_rate = sum(item.annotator_b for item in labels) / total
    expected_agreement = a_true_rate * b_true_rate + (1 - a_true_rate) * (1 - b_true_rate)
    denominator = 1 - expected_agreement
    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return None
    return (observed_agreement - expected_agreement) / denominator


def calculate_metrics(
    labels_by_key: dict[ClaimKey, ClaimLabels], record_count: int, input_path: Path
) -> dict[str, Any]:
    """基于全部 claim 计算论文表 V 的五项指标。"""

    labels = list(labels_by_key.values())
    total_claim_count = len(labels)
    human_correct_count = sum(item.final_human for item in labels)
    judge_correct_count = sum(item.machine for item in labels)
    human_human_agreement_count = sum(
        item.annotator_a == item.annotator_b for item in labels
    )
    judge_human_agreement_count = sum(item.machine == item.final_human for item in labels)
    third_adjudication_count = sum(item.requires_third_annotator for item in labels)

    return {
        "input_json": str(input_path),
        "record_count": record_count,
        "total_claim_count": total_claim_count,
        "annotator_disagreement_count": third_adjudication_count,
        "third_adjudication_count": third_adjudication_count,
        "metrics": {
            "human_claim_correct_rate": safe_percentage(human_correct_count, total_claim_count),
            "judge_claim_correct_rate": safe_percentage(judge_correct_count, total_claim_count),
            "human_human_raw_agreement": safe_percentage(
                human_human_agreement_count, total_claim_count
            ),
            "human_human_cohens_kappa": cohens_kappa(labels),
            "judge_human_agreement": safe_percentage(
                judge_human_agreement_count, total_claim_count
            ),
        },
    }


def main() -> int:
    """执行读取、统计并向标准输出打印 JSON。"""

    args = build_parser().parse_args()
    try:
        labels, record_count = load_claim_labels(args.input_json)
        result = calculate_metrics(labels, record_count, args.input_json)
    except ClaimJudgmentMetricsError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["metrics"]["human_human_cohens_kappa"] is None:
        print("说明：A/B 标签边际分布使 Cohen's kappa 不可定义。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
