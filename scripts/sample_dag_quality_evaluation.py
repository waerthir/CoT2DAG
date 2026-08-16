"""按学科和难度分层抽取 DAG 质量评分结果，并统计六项评分。"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


NODE_METRICS = (
    "Information_Fidelity",
    "Claim_Atomicity",
    "Node_Type_Correctness",
    "Dependency_Completeness",
    "Dependency_Correctness",
)
COMMON_NODE_METRICS = NODE_METRICS[:3]
DEPENDENCY_METRICS = NODE_METRICS[3:]
GRAPH_METRIC = "Information_Coverage"
ALL_GRAPH_METRICS = (*NODE_METRICS, GRAPH_METRIC)
PASS_THRESHOLD = 6.0


class SamplingDataError(ValueError):
    """输入文件、关联关系或评分字段不符合抽样要求时抛出。"""


@dataclass(frozen=True)
class Stratum:
    """一个由学科和难度共同确定的稳定分层。"""

    subject_dir: str
    difficulty_level: str


@dataclass(frozen=True)
class Candidate:
    """一条可参与分层抽样的质量评估记录。"""

    batch_id: str
    stratum: Stratum
    selection_score: float
    record: dict[str, Any]


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="DAG 质量评分结果的分层抽样与统计")
    parser.add_argument("--input-json", type=Path, required=True, help="单个 DAG 质量评估导出 JSON")
    parser.add_argument(
        "--selection-json",
        type=Path,
        required=True,
        help="包含 sample_id、subject_dir、difficulty_level 的分层元数据 JSON",
    )
    parser.add_argument("--output-json", type=Path, required=True, help="抽样统计 JSON 输出路径")
    parser.add_argument("--mode", choices=("best", "random"), required=True, help="抽样模式")
    parser.add_argument("--sample-count", type=int, default=200, help="总抽样数，默认 200")
    parser.add_argument("--seed", type=int, help="random 模式的可复现随机种子")
    return parser


def _load_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    """读取一个顶层为对象列表的 JSON 文件。"""

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SamplingDataError(f"{description}文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SamplingDataError(f"{description}不是合法 JSON：{path}；{exc}") from exc
    if not isinstance(raw_data, list):
        raise SamplingDataError(f"{description}顶层必须是列表：{path}")
    if not all(isinstance(item, dict) for item in raw_data):
        raise SamplingDataError(f"{description}列表中的每一项必须是对象：{path}")
    return raw_data


def _nonempty_string(value: Any, field_name: str, source: str) -> str:
    """读取非空字符串字段。"""

    if not isinstance(value, str) or not value:
        raise SamplingDataError(f"{source}的 {field_name} 必须是非空字符串。")
    return value


def _score(value: Any, field_name: str, source: str) -> float:
    """读取有限且位于 0 至 10 的评分。"""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SamplingDataError(f"{source}的 {field_name} 必须是数值评分。")
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 10:
        raise SamplingDataError(f"{source}的 {field_name} 必须在 0 到 10 之间。")
    return score


def load_strata(selection_path: Path) -> tuple[list[Stratum], dict[str, Stratum]]:
    """读取分层元数据，并保留其首次出现顺序。"""

    strata_order: list[Stratum] = []
    seen_strata: set[Stratum] = set()
    metadata_by_id: dict[str, Stratum] = {}
    for index, item in enumerate(_load_json_list(selection_path, "分层元数据")):
        source = f"分层元数据第 {index} 条"
        sample_id = _nonempty_string(item.get("sample_id"), "sample_id", source)
        if sample_id in metadata_by_id:
            raise SamplingDataError(f"分层元数据中的 sample_id 重复：{sample_id}")
        stratum = Stratum(
            subject_dir=_nonempty_string(item.get("subject_dir"), "subject_dir", source),
            difficulty_level=_nonempty_string(
                item.get("difficulty_level"), "difficulty_level", source
            ),
        )
        metadata_by_id[sample_id] = stratum
        if stratum not in seen_strata:
            strata_order.append(stratum)
            seen_strata.add(stratum)
    if not strata_order:
        raise SamplingDataError("分层元数据为空，无法进行抽样。")
    return strata_order, metadata_by_id


def _selection_score(record: dict[str, Any], source: str) -> float:
    """计算 best 模式使用的六项图级评分等权平均值。"""

    dag_evaluation = record.get("dag_evaluation")
    if not isinstance(dag_evaluation, dict):
        raise SamplingDataError(f"{source}缺少 dag_evaluation 对象。")
    return sum(
        _score(dag_evaluation.get(metric), metric, source) for metric in ALL_GRAPH_METRICS
    ) / len(ALL_GRAPH_METRICS)


def load_candidates(
    input_path: Path, metadata_by_id: dict[str, Stratum]
) -> list[Candidate]:
    """读取质量评估导出文件，并按 batch_id 关联分层元数据。"""

    candidates: list[Candidate] = []
    seen_batch_ids: set[str] = set()
    for index, record in enumerate(_load_json_list(input_path, "质量评估导出")):
        source = f"质量评估导出第 {index} 条"
        batch_id = _nonempty_string(record.get("batch_id"), "batch_id", source)
        if batch_id in seen_batch_ids:
            raise SamplingDataError(f"质量评估导出中的 batch_id 重复：{batch_id}")
        seen_batch_ids.add(batch_id)
        stratum = metadata_by_id.get(batch_id)
        if stratum is None:
            raise SamplingDataError(
                f"质量评估导出的 batch_id 在分层元数据中不存在：{batch_id}"
            )
        candidates.append(
            Candidate(
                batch_id=batch_id,
                stratum=stratum,
                selection_score=_selection_score(record, source),
                record=record,
            )
        )
    return candidates


def _quotas(strata: list[Stratum], sample_count: int) -> dict[Stratum, int]:
    """按稳定分层顺序尽量平均地分配总样本数。"""

    if sample_count <= 0:
        raise SamplingDataError("sample-count 必须是正整数。")
    base_count, remainder = divmod(sample_count, len(strata))
    return {
        stratum: base_count + int(index < remainder)
        for index, stratum in enumerate(strata)
    }


def select_candidates(
    candidates: list[Candidate],
    strata: list[Stratum],
    quotas: dict[Stratum, int],
    mode: str,
    seed: int | None,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """按配额从每一层选择最优或随机样本。"""

    candidates_by_stratum: dict[Stratum, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        candidates_by_stratum[candidate.stratum].append(candidate)

    stratum_reports: list[dict[str, Any]] = []
    for stratum in strata:
        available_count = len(candidates_by_stratum[stratum])
        target_count = quotas[stratum]
        stratum_reports.append(
            {
                "subject_dir": stratum.subject_dir,
                "difficulty_level": stratum.difficulty_level,
                "target_count": target_count,
                "available_count": available_count,
            }
        )
        if available_count < target_count:
            raise SamplingDataError(
                "分层候选不足："
                f"subject_dir={stratum.subject_dir}，"
                f"difficulty_level={stratum.difficulty_level}，"
                f"需求={target_count}，可用={available_count}。"
            )

    rng = random.Random(seed)
    selected: list[Candidate] = []
    for report, stratum in zip(stratum_reports, strata, strict=True):
        pool = candidates_by_stratum[stratum]
        target_count = quotas[stratum]
        if mode == "best":
            chosen = sorted(pool, key=lambda item: (-item.selection_score, item.batch_id))[
                :target_count
            ]
        else:
            chosen = rng.sample(sorted(pool, key=lambda item: item.batch_id), target_count)
        chosen = sorted(chosen, key=lambda item: item.batch_id)
        selected.extend(chosen)
        report["selected_count"] = len(chosen)
    return selected, stratum_reports


def _metric_statistics(values: Iterable[float]) -> dict[str, float | int]:
    """计算一个指标的均值、通过数量、总数量和通过率。"""

    value_list = list(values)
    if not value_list:
        raise SamplingDataError("统计指标没有可用评分。")
    passed_count = sum(value >= PASS_THRESHOLD for value in value_list)
    return {
        "mean": sum(value_list) / len(value_list),
        "passed_count": passed_count,
        "total_count": len(value_list),
        "pass_rate": passed_count / len(value_list),
    }


def calculate_statistics(selected: list[Candidate]) -> dict[str, dict[str, float | int]]:
    """按节点或按图分别计算六项指标统计值。"""

    metric_values: dict[str, list[float]] = {metric: [] for metric in ALL_GRAPH_METRICS}
    for candidate in selected:
        source = f"batch_id={candidate.batch_id}"
        node_evaluations = candidate.record.get("node_evaluations")
        if not isinstance(node_evaluations, list) or not node_evaluations:
            raise SamplingDataError(f"{source}缺少非空 node_evaluations 列表。")
        for node_index, node in enumerate(node_evaluations):
            if not isinstance(node, dict):
                raise SamplingDataError(f"{source}第 {node_index} 个节点评分必须是对象。")
            node_source = f"{source} 的节点 {node_index}"
            for metric in COMMON_NODE_METRICS:
                metric_values[metric].append(_score(node.get(metric), metric, node_source))
            supplied_dependency_metrics = [metric in node for metric in DEPENDENCY_METRICS]
            if any(supplied_dependency_metrics) and not all(supplied_dependency_metrics):
                raise SamplingDataError(f"{node_source}的两项 Dependency 评分必须同时出现。")
            if all(supplied_dependency_metrics):
                for metric in DEPENDENCY_METRICS:
                    metric_values[metric].append(_score(node.get(metric), metric, node_source))
        dag_evaluation = candidate.record["dag_evaluation"]
        metric_values[GRAPH_METRIC].append(
            _score(dag_evaluation.get(GRAPH_METRIC), GRAPH_METRIC, source)
        )
    return {metric: _metric_statistics(values) for metric, values in metric_values.items()}


def build_output(
    args: argparse.Namespace,
    selected: list[Candidate],
    strata: list[dict[str, Any]],
    statistics: dict[str, dict[str, float | int]],
) -> dict[str, Any]:
    """构造稳定排序的抽样结果与统计输出。"""

    return {
        "parameters": {
            "input_json": str(args.input_json),
            "selection_json": str(args.selection_json),
            "mode": args.mode,
            "sample_count": args.sample_count,
            "seed": args.seed,
            "pass_threshold": PASS_THRESHOLD,
        },
        "actual_sample_count": len(selected),
        "strata": strata,
        "selected_items": [
            {
                "batch_id": candidate.batch_id,
                "subject_dir": candidate.stratum.subject_dir,
                "difficulty_level": candidate.stratum.difficulty_level,
                "selection_score": candidate.selection_score,
            }
            for candidate in selected
        ],
        "statistics": statistics,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写入 JSON，避免中断时留下不完整输出文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(path)


def main() -> int:
    """执行单个质量评估文件的分层抽样与统计。"""

    args = build_parser().parse_args()
    try:
        strata, metadata_by_id = load_strata(args.selection_json)
        candidates = load_candidates(args.input_json, metadata_by_id)
        quotas = _quotas(strata, args.sample_count)
        selected, stratum_reports = select_candidates(
            candidates, strata, quotas, args.mode, args.seed
        )
        if len(selected) != args.sample_count:
            raise SamplingDataError(
                f"抽样结果数量异常：期望 {args.sample_count}，实际 {len(selected)}。"
            )
        output = build_output(
            args, selected, stratum_reports, calculate_statistics(selected)
        )
        write_json(args.output_json, output)
    except SamplingDataError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    print(f"已抽取 {len(selected)} 条记录：{args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
