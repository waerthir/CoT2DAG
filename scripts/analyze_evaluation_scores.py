"""统计评分结果 JSON，并生成文本报告和各指标的分布汇总图。"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORE_MINIMUM = 0.0
SCORE_MAXIMUM = 10.0


class EvaluationAnalysisError(ValueError):
    """输入路径、参数或评分 JSON 不符合统计要求时抛出的异常。"""


@dataclass(frozen=True)
class MetricStatistics:
    """保存一个评分指标的统计结果，供报告和图表共同使用。"""

    field_name: str
    display_name: str
    scores: list[float]
    mean: float
    variance: float
    qualified_count: int

    @property
    def total_count(self) -> int:
        """返回该指标实际参与统计的评分数量。"""

        return len(self.scores)

    @property
    def qualified_rate(self) -> float:
        """返回该指标的合格率百分比。"""

        return self.qualified_count / self.total_count * 100


def build_parser() -> argparse.ArgumentParser:
    """创建并返回评分统计脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="统计评分结果 JSON，并输出文本报告与分布汇总图。"
    )
    parser.add_argument("input_json", type=Path, help="评分结果 JSON 路径")
    parser.add_argument("report_output", type=Path, help="统计文本报告输出路径")
    parser.add_argument("figure_output", type=Path, help="汇总 PNG 图输出路径")
    parser.add_argument(
        "--threshold",
        type=float,
        required=True,
        help="合格阈值；分数大于或等于该值时计为合格",
    )
    parser.add_argument(
        "--metrics",
        required=True,
        help=(
            "JSON 对象：键为 evaluation 内的指标字段名，值为报告和图表使用的显示名称；"
            '例如 {"Fidelity":"信息忠实度","Atomicity":"原子化程度"}'
        ),
    )
    return parser


def resolve_project_path(path: Path) -> Path:
    """将相对路径按项目根目录解析，绝对路径保持不变。"""

    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def parse_metrics(raw_metrics: str) -> dict[str, str]:
    """解析并检查“指标字段名到显示名称”的 JSON 字典参数。"""

    try:
        metrics = json.loads(raw_metrics)
    except json.JSONDecodeError as exc:
        raise EvaluationAnalysisError(f"--metrics 不是合法 JSON 对象：{exc}") from exc

    if not isinstance(metrics, dict) or not metrics:
        raise EvaluationAnalysisError("--metrics 必须是非空 JSON 对象")

    parsed_metrics: dict[str, str] = {}
    for field_name, display_name in metrics.items():
        if not isinstance(field_name, str) or not field_name.strip():
            raise EvaluationAnalysisError("--metrics 中的指标字段名必须是非空字符串")
        if not isinstance(display_name, str) or not display_name.strip():
            raise EvaluationAnalysisError(
                f"指标 {field_name!r} 的显示名称必须是非空字符串"
            )
        parsed_metrics[field_name] = display_name
    return parsed_metrics


def validate_threshold(threshold: float) -> float:
    """检查合格阈值为 0 至 10 范围内的有限浮点数。"""

    if not math.isfinite(threshold):
        raise EvaluationAnalysisError("合格阈值必须是有限数值")
    if not SCORE_MINIMUM <= threshold <= SCORE_MAXIMUM:
        raise EvaluationAnalysisError("合格阈值必须位于 0 至 10 的范围内")
    return threshold


def validate_paths(
    input_path: Path, report_path: Path, figure_path: Path
) -> tuple[Path, Path, Path]:
    """解析输入输出路径，并阻止报告、图片或输入文件发生路径覆盖。"""

    resolved_paths = tuple(
        resolve_project_path(path) for path in (input_path, report_path, figure_path)
    )
    if len(set(resolved_paths)) != len(resolved_paths):
        raise EvaluationAnalysisError("输入 JSON、文本报告和图片输出路径必须两两不同")
    if figure_path.suffix.lower() != ".png":
        raise EvaluationAnalysisError("汇总图输出路径必须使用 .png 后缀")
    return resolved_paths


def load_score_records(input_path: Path) -> list[dict[str, Any]]:
    """读取评分 JSON，并检查其顶层为由对象组成的列表。"""

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationAnalysisError(f"输入评分文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationAnalysisError(f"输入评分文件不是合法 JSON：{exc}") from exc

    if not isinstance(data, list):
        raise EvaluationAnalysisError("输入评分 JSON 的顶层必须是列表")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise EvaluationAnalysisError(f"输入评分 JSON 的第 {index} 项必须是对象")
        records.append(item)
    return records


def extract_metric_scores(
    records: list[dict[str, Any]], metrics: dict[str, str]
) -> dict[str, list[float]]:
    """从每条记录的 evaluation 对象提取选定指标的有效评分。"""

    extracted = {field_name: [] for field_name in metrics}
    for record_index, record in enumerate(records):
        evaluation = record.get("evaluation")
        if not isinstance(evaluation, dict):
            raise EvaluationAnalysisError(
                f"输入评分 JSON 的第 {record_index} 项缺少 evaluation 对象"
            )

        for field_name in metrics:
            if field_name not in evaluation:
                continue
            raw_score = evaluation[field_name]
            if isinstance(raw_score, bool):
                raise EvaluationAnalysisError(
                    f"第 {record_index} 项的 {field_name} 必须是数值，不能是布尔值"
                )
            try:
                score = float(raw_score)
            except (TypeError, ValueError) as exc:
                raise EvaluationAnalysisError(
                    f"第 {record_index} 项的 {field_name} 不是有效数值"
                ) from exc
            if not math.isfinite(score) or not SCORE_MINIMUM <= score <= SCORE_MAXIMUM:
                raise EvaluationAnalysisError(
                    f"第 {record_index} 项的 {field_name} 必须是 0 至 10 的有限数值"
                )
            extracted[field_name].append(score)

    missing_metrics = [name for name, scores in extracted.items() if not scores]
    if missing_metrics:
        raise EvaluationAnalysisError(
            "以下指定指标没有任何有效分数：" + "、".join(missing_metrics)
        )
    return extracted


def calculate_statistics(
    extracted_scores: dict[str, list[float]], metrics: dict[str, str], threshold: float
) -> list[MetricStatistics]:
    """计算每个指标的均值、总体方差和合格统计。"""

    statistics: list[MetricStatistics] = []
    for field_name, display_name in metrics.items():
        scores = extracted_scores[field_name]
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        qualified_count = sum(score >= threshold for score in scores)
        statistics.append(
            MetricStatistics(
                field_name=field_name,
                display_name=display_name,
                scores=scores,
                mean=mean,
                variance=variance,
                qualified_count=qualified_count,
            )
        )
    return statistics


def build_report(
    input_path: Path, threshold: float, statistics: list[MetricStatistics]
) -> str:
    """构建包含每个指标统计结果的 UTF-8 文本报告内容。"""

    lines = [
        "评分结果统计报告",
        f"输入文件：{input_path}",
        f"合格阈值：{threshold:g}",
        "",
    ]
    for item in statistics:
        lines.extend(
            [
                f"指标：{item.display_name}（{item.field_name}）",
                f"均值：{item.mean:.4f}",
                f"总体方差：{item.variance:.4f}",
                f"合格数量/总数量：{item.qualified_count}/{item.total_count}",
                f"合格率：{item.qualified_rate:.2f}%",
                "",
            ]
        )
    return "\n".join(lines)


def write_text_atomically(path: Path, content: str) -> None:
    """将文本先写入临时文件，再原子替换为目标报告文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def configure_plot_style() -> None:
    """配置汇总图的网格风格及常见中文字体回退列表。"""

    sns.set_theme(
        style="whitegrid",
        rc={
            "font.sans-serif": ["SimHei", "Microsoft YaHei", "Arial Unicode MS"],
            "axes.unicode_minus": False,
        },
    )


def should_draw_kde(scores: list[float]) -> bool:
    """仅在分数数量和离散程度足够时绘制 KDE，避免退化数据的绘图警告。"""

    return len(scores) >= 2 and min(scores) != max(scores)


def write_figure(
    figure_path: Path, threshold: float, statistics: list[MetricStatistics]
) -> None:
    """绘制各指标直方图、KDE 曲线与合格阈值线，并保存为 PNG。"""

    configure_plot_style()
    column_count = 2
    row_count = math.ceil(len(statistics) / column_count)
    figure, axes = plt.subplots(
        row_count, column_count, figsize=(12, 5 * row_count), squeeze=False
    )
    flat_axes = axes.flatten()
    bins = [score - 0.5 for score in range(12)]
    color = sns.color_palette("viridis")[3]

    for axis, item in zip(flat_axes, statistics):
        sns.histplot(
            item.scores,
            bins=bins,
            kde=should_draw_kde(item.scores),
            color=color,
            edgecolor="black",
            ax=axis,
        )
        axis.axvline(threshold, color="crimson", linestyle="--", linewidth=1.5)
        axis.set_title(
            f"{item.display_name}\n"
            f"合格（≥ {threshold:g}）：{item.qualified_count}/{item.total_count} "
            f"({item.qualified_rate:.1f}%)",
            fontsize=12,
        )
        axis.set_xlabel("分数（0–10）")
        axis.set_ylabel("频数")
        axis.set_xlim(-0.5, 10.5)
        axis.set_xticks(range(11))

    for axis in flat_axes[len(statistics) :]:
        axis.axis("off")

    figure.tight_layout()
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = figure_path.with_suffix(figure_path.suffix + ".tmp")
    figure.savefig(temporary_path, format="png", dpi=150)
    plt.close(figure)
    temporary_path.replace(figure_path)


def execute(
    input_path: Path,
    report_path: Path,
    figure_path: Path,
    threshold: float,
    raw_metrics: str,
) -> int:
    """完成评分读取、统计计算、报告写入和汇总图生成。"""

    input_path, report_path, figure_path = validate_paths(
        input_path, report_path, figure_path
    )
    threshold = validate_threshold(threshold)
    metrics = parse_metrics(raw_metrics)
    records = load_score_records(input_path)
    extracted_scores = extract_metric_scores(records, metrics)
    statistics = calculate_statistics(extracted_scores, metrics, threshold)

    write_text_atomically(report_path, build_report(input_path, threshold, statistics))
    write_figure(figure_path, threshold, statistics)

    print(f"输入记录数：{len(records)}")
    print(f"合格阈值：{threshold:g}")
    for item in statistics:
        print(
            f"{item.display_name}：均值={item.mean:.4f}，"
            f"合格={item.qualified_count}/{item.total_count}（{item.qualified_rate:.2f}%）"
        )
    print(f"文本报告：{report_path}")
    print(f"汇总图：{figure_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(
            args.input_json,
            args.report_output,
            args.figure_output,
            args.threshold,
            args.metrics,
        )
    except EvaluationAnalysisError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())



'''
python scripts\analyze_evaluation_scores.py `
  data\cot-1\llava-cot-11b\node_eval.json `
  data\cot-1\llava-cot-11b\node_stat.txt `
  data\cot-1\llava-cot-11b\node_stat.png `
  --threshold 6 `
  --metrics '{\"Fidelity\":\"信息忠实度\",\"Atomicity\":\"原子化程度\"}'
'''

'''
python scripts\analyze_evaluation_scores.py `
  data\cot-1\llava-cot-11b\rel_eval.json `
  data\cot-1\llava-cot-11b\rel_stat.txt `
  data\cot-1\llava-cot-11b\rel_stat.png `
  --threshold 6 `
  --metrics '{\"Dependency_Completeness\":\"依赖关系完整性\",\"Dependency_Accuracy\":\"依赖关系准确性\",\"Reasoning_Logic_Accuracy\":\"推理逻辑准确性\",\"Reasoning_Type_Accuracy\":\"推理类型准确性\"}'
'''



'''
python scripts\analyze_evaluation_scores.py `
  data\cot-1\gemini-3.1pro\node_eval.json `
  data\cot-1\gemini-3.1pro\node_stat.txt `
  data\cot-1\gemini-3.1pro\node_stat.png `
  --threshold 6 `
  --metrics '{\"Fidelity\":\"信息忠实度\",\"Atomicity\":\"原子化程度\"}'

python scripts\analyze_evaluation_scores.py `
  data\cot-1\gemini-3.1pro\rel_eval.json `
  data\cot-1\gemini-3.1pro\rel_stat.txt `
  data\cot-1\gemini-3.1pro\rel_stat.png `
  --threshold 6 `
  --metrics '{\"Dependency_Completeness\":\"依赖关系完整性\",\"Dependency_Accuracy\":\"依赖关系准确性\",\"Reasoning_Logic_Accuracy\":\"推理逻辑准确性\",\"Reasoning_Type_Accuracy\":\"推理类型准确性\"}'
'''