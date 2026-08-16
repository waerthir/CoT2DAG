"""从多个 API 原始数据 JSON 的共同样本中进行分层随机抽样。"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


SUBJECTS = (
    "math",
    "physics",
    "circuit",
    "chemistry",
    "geography",
    "biology",
)
DIFFICULTIES = ("medium", "medium_high", "high")
STRATA = tuple((subject, difficulty) for subject in SUBJECTS for difficulty in DIFFICULTIES)
DEFAULT_SAMPLE_SIZE = 400
DEFAULT_SEED = 20260816


class SharedSamplingError(ValueError):
    """输入文件、共同样本或分层配额不符合抽样要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回本脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="从多个 API 原始 JSON 的共同 sample_id 中进行三难度六学科分层抽样。"
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        action="append",
        required=True,
        metavar="PATH",
        help="API 原始数据 JSON 路径；至少传入两次，每次传入一个路径",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        metavar="PATH",
        help="抽样结果 JSON 输出路径",
    )
    parser.add_argument(
        "--sample-size",
        type=_positive_integer,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"总抽样数量，默认 {DEFAULT_SAMPLE_SIZE}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"随机种子，默认 {DEFAULT_SEED}",
    )
    return parser


def _positive_integer(value: str) -> int:
    """将命令行字符串转换为正整数；非法值交给 argparse 报错。"""

    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("抽样数量必须是正整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("抽样数量必须是正整数")
    return number


def require_nonempty_string(value: Any, field_name: str, record_label: str) -> str:
    """读取记录中的非空字符串字段，并在字段无效时给出定位信息。"""

    if not isinstance(value, str) or not value.strip():
        raise SharedSamplingError(f"{record_label} 缺少非空字符串字段 {field_name}。")
    return value


def validate_paths(input_paths: list[Path], output_path: Path) -> tuple[list[Path], Path]:
    """解析路径，要求至少两个不同输入，并阻止输出覆盖输入。"""

    if len(input_paths) < 2:
        raise SharedSamplingError("--input-json 至少需要传入两次。")

    resolved_inputs = [path.resolve() for path in input_paths]
    if len(set(resolved_inputs)) != len(resolved_inputs):
        raise SharedSamplingError("--input-json 不能重复传入同一个文件。")

    resolved_output = output_path.resolve()
    if resolved_output in set(resolved_inputs):
        raise SharedSamplingError("输出路径不能覆盖任一输入 JSON。")
    return resolved_inputs, resolved_output


def load_json_list(path: Path) -> list[dict[str, Any]]:
    """读取一个顶层为对象列表的原始数据 JSON 文件。"""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SharedSamplingError(f"输入文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SharedSamplingError(f"输入文件不是合法 JSON：{path}；{exc}") from exc

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SharedSamplingError(f"输入 JSON 必须是由对象组成的列表：{path}")
    return value


def build_metadata_index(
    items: list[dict[str, Any]], input_path: Path
) -> dict[str, tuple[str, str]]:
    """提取 sample_id、学科和难度，并检查单个输入中的 sample_id 唯一性。"""

    metadata_by_id: dict[str, tuple[str, str]] = {}
    for index, item in enumerate(items, start=1):
        record_label = f"{input_path} 第 {index} 条"
        sample_id = require_nonempty_string(item.get("sample_id"), "sample_id", record_label)
        subject = require_nonempty_string(item.get("subject_dir"), "subject_dir", record_label)
        difficulty = require_nonempty_string(
            item.get("difficulty_level"), "difficulty_level", record_label
        )
        if sample_id in metadata_by_id:
            raise SharedSamplingError(f"{input_path} 存在重复 sample_id：{sample_id}")
        metadata_by_id[sample_id] = (subject, difficulty)
    return metadata_by_id


def build_shared_metadata(
    metadata_indexes: list[dict[str, tuple[str, str]]]
) -> dict[str, tuple[str, str]]:
    """取精确 sample_id 交集，并确认共同记录的学科和难度完全一致。"""

    common_ids = set.intersection(*(set(index) for index in metadata_indexes))
    if not common_ids:
        raise SharedSamplingError("输入文件之间不存在共同 sample_id，无法抽样。")

    shared_metadata: dict[str, tuple[str, str]] = {}
    first_index = metadata_indexes[0]
    for sample_id in sorted(common_ids):
        expected_metadata = first_index[sample_id]
        for input_index, metadata_index in enumerate(metadata_indexes[1:], start=2):
            actual_metadata = metadata_index[sample_id]
            if actual_metadata != expected_metadata:
                raise SharedSamplingError(
                    f"共同 sample_id 的元数据不一致：{sample_id}；"
                    f"输入 1 为 subject_dir={expected_metadata[0]!r}、"
                    f"difficulty_level={expected_metadata[1]!r}，"
                    f"输入 {input_index} 为 subject_dir={actual_metadata[0]!r}、"
                    f"difficulty_level={actual_metadata[1]!r}。"
                )
        shared_metadata[sample_id] = expected_metadata
    return shared_metadata


def build_strata(
    shared_metadata: dict[str, tuple[str, str]]
) -> dict[tuple[str, str], list[str]]:
    """按既定六学科与三难度将共同样本分入 18 个分层。"""

    candidates_by_stratum = {stratum: [] for stratum in STRATA}
    for sample_id, (subject, difficulty) in shared_metadata.items():
        stratum = (subject, difficulty)
        if stratum in candidates_by_stratum:
            candidates_by_stratum[stratum].append(sample_id)
    for sample_ids in candidates_by_stratum.values():
        sample_ids.sort()
    return candidates_by_stratum


def build_quotas(sample_size: int) -> dict[tuple[str, str], int]:
    """将总抽样数量尽量均衡地分配至固定的 18 个分层。"""

    base_count, remainder = divmod(sample_size, len(STRATA))
    return {
        stratum: base_count + int(index < remainder)
        for index, stratum in enumerate(STRATA)
    }


def validate_capacity(
    candidates_by_stratum: dict[tuple[str, str], list[str]],
    quotas: dict[tuple[str, str], int],
) -> None:
    """确认每个分层都拥有满足其抽样配额的共同样本。"""

    insufficient = [
        (stratum, len(candidates_by_stratum[stratum]), quotas[stratum])
        for stratum in STRATA
        if len(candidates_by_stratum[stratum]) < quotas[stratum]
    ]
    if not insufficient:
        return

    details = ["以下分层的共同样本不足所需抽样配额："]
    details.extend(
        f"{subject}/{difficulty}：可用 {available} 条，需 {required} 条"
        for (subject, difficulty), available, required in insufficient
    )
    raise SharedSamplingError("\n".join(details))


def sample_ids(
    candidates_by_stratum: dict[tuple[str, str], list[str]],
    quotas: dict[tuple[str, str], int],
    seed: int,
) -> list[str]:
    """按固定分层顺序及给定随机种子抽取 sample_id。"""

    random_generator = random.Random(seed)
    selected_ids: list[str] = []
    for stratum in STRATA:
        selected_ids.extend(
            random_generator.sample(candidates_by_stratum[stratum], quotas[stratum])
        )
    return selected_ids


def write_output(output_path: Path, selected_ids: list[str]) -> None:
    """先写入同目录临时文件，再原子替换为正式 JSON 输出文件。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(selected_ids, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def print_summary(
    input_paths: list[Path],
    input_counts: list[int],
    shared_metadata: dict[str, tuple[str, str]],
    candidates_by_stratum: dict[tuple[str, str], list[str]],
    quotas: dict[tuple[str, str], int],
    selected_ids: list[str],
    output_path: Path,
) -> None:
    """打印输入、交集、分层和输出的抽样摘要。"""

    print(f"输入文件数量：{len(input_paths)}")
    for index, (input_path, count) in enumerate(zip(input_paths, input_counts), start=1):
        print(f"输入 {index}：{input_path}（{count} 条）")
    print(f"精确 sample_id 交集条数：{len(shared_metadata)}")
    print(f"三难度六学科候选条数：{sum(map(len, candidates_by_stratum.values()))}")
    for subject, difficulty in STRATA:
        stratum = (subject, difficulty)
        print(
            f"{subject}/{difficulty}："
            f"可用 {len(candidates_by_stratum[stratum])} 条，"
            f"抽取 {quotas[stratum]} 条"
        )
    print(f"总抽样数：{len(selected_ids)}")
    print(f"输出文件：{output_path}")


def execute(
    input_paths: list[Path], output_path: Path, sample_size: int, seed: int
) -> int:
    """完成读取、求交、分层、随机抽样、写出与结果提示。"""

    input_paths, output_path = validate_paths(input_paths, output_path)
    input_items = [load_json_list(input_path) for input_path in input_paths]
    metadata_indexes = [
        build_metadata_index(items, input_path)
        for input_path, items in zip(input_paths, input_items, strict=True)
    ]
    shared_metadata = build_shared_metadata(metadata_indexes)
    candidates_by_stratum = build_strata(shared_metadata)
    quotas = build_quotas(sample_size)
    validate_capacity(candidates_by_stratum, quotas)
    selected_ids = sample_ids(candidates_by_stratum, quotas, seed)
    write_output(output_path, selected_ids)
    print_summary(
        input_paths,
        [len(items) for items in input_items],
        shared_metadata,
        candidates_by_stratum,
        quotas,
        selected_ids,
        output_path,
    )
    return 0


def main() -> int:
    """解析命令行参数，并将预期输入错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json, args.output_json, args.sample_size, args.seed)
    except SharedSamplingError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
