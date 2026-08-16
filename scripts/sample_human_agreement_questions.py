"""从共同 200 题名单中固定随机抽取人工一致性验证的 50 题。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


class HumanAgreementSamplingError(ValueError):
    """二次抽样输入或输出不符合要求时抛出。"""


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="从共同 200 题中抽取人工一致性验证题目")
    parser.add_argument("--input-json", type=Path, required=True, help="含 selected_items 的 200 题抽样 JSON")
    parser.add_argument("--output-json", type=Path, required=True, help="共同 50 题名单输出路径")
    parser.add_argument("--sample-count", type=int, default=50, help="二次抽样数量，默认 50")
    parser.add_argument("--seed", type=int, required=True, help="用于可复现抽样的固定随机种子")
    return parser


def load_selected_items(input_path: Path) -> list[dict[str, Any]]:
    """读取并检查输入统计 JSON 中的 selected_items。"""

    try:
        raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HumanAgreementSamplingError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise HumanAgreementSamplingError(f"输入文件不是合法 JSON：{input_path}；{exc}") from exc
    if not isinstance(raw_data, dict):
        raise HumanAgreementSamplingError("输入 JSON 顶层必须是对象。")

    selected_items = raw_data.get("selected_items")
    if not isinstance(selected_items, list):
        raise HumanAgreementSamplingError("输入 JSON 缺少 selected_items 列表。")

    seen_batch_ids: set[str] = set()
    for index, item in enumerate(selected_items):
        source = f"selected_items 第 {index} 条"
        if not isinstance(item, dict):
            raise HumanAgreementSamplingError(f"{source}必须是对象。")
        for field_name in ("batch_id", "subject_dir", "difficulty_level"):
            value = item.get(field_name)
            if not isinstance(value, str) or not value:
                raise HumanAgreementSamplingError(f"{source}的 {field_name} 必须是非空字符串。")
        selection_score = item.get("selection_score")
        if isinstance(selection_score, bool) or not isinstance(selection_score, (int, float)):
            raise HumanAgreementSamplingError(f"{source}的 selection_score 必须是数值。")
        batch_id = item["batch_id"]
        if batch_id in seen_batch_ids:
            raise HumanAgreementSamplingError(f"selected_items 中存在重复 batch_id：{batch_id}")
        seen_batch_ids.add(batch_id)
    return selected_items


def sample_items(
    selected_items: list[dict[str, Any]], sample_count: int, seed: int
) -> list[dict[str, Any]]:
    """按固定种子无放回抽样，并恢复输入中的原始顺序。"""

    if sample_count <= 0:
        raise HumanAgreementSamplingError("sample-count 必须是正整数。")
    if len(selected_items) < sample_count:
        raise HumanAgreementSamplingError(
            f"selected_items 数量不足：需要 {sample_count}，实际只有 {len(selected_items)}。"
        )
    sampled_indices = random.Random(seed).sample(range(len(selected_items)), sample_count)
    return [selected_items[index] for index in sorted(sampled_indices)]


def write_output(
    output_path: Path,
    input_path: Path,
    sample_count: int,
    seed: int,
    selected_items: list[dict[str, Any]],
) -> None:
    """以原子替换方式写入共同的人工一致性验证名单。"""

    output = {
        "source_input_json": str(input_path),
        "sample_count": sample_count,
        "actual_sample_count": len(selected_items),
        "seed": seed,
        "selected_items": selected_items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(output_path)


def main() -> int:
    """执行二次随机抽样。"""

    args = build_parser().parse_args()
    try:
        input_items = load_selected_items(args.input_json)
        sampled_items = sample_items(input_items, args.sample_count, args.seed)
        write_output(
            args.output_json,
            args.input_json,
            args.sample_count,
            args.seed,
            sampled_items,
        )
    except HumanAgreementSamplingError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    print(f"已从 {len(input_items)} 条共同样本中抽取 {len(sampled_items)} 条：{args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
