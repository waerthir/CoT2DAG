"""将 DAG、题目资源和 Ground Truth 整理为图级评估输入。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any, Literal


IMAGE_REMOTE_ROOT = "/home/lijingyue/qiujianbo/ready/"
IMAGE_LOCAL_ROOT = Path("data/download/ready")
ITEM_REMOTE_ROOT = "/home/lijingyue/LiangEnRui/"
ITEM_LOCAL_ROOT = Path("data/download")
IdMode = Literal["problem-id", "source-order"]


class CombineBuildError(ValueError):
    """DAG、来源记录或本地资源不能组成完整 combine 文件时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回 combine 整理脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="将 DAG 与原始题目记录整理为图级评估的 combine.json。"
    )
    parser.add_argument("dag_json", type=Path, help="输入 dag.json 路径")
    parser.add_argument("source_json", type=Path, help="对应原始记录 JSON 路径")
    parser.add_argument("output_json", type=Path, help="输出 combine.json 路径")
    parser.add_argument(
        "--id-mode",
        choices=("problem-id", "source-order"),
        required=True,
        help="DAG 与原始记录的对齐方式",
    )
    return parser


def load_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    """读取 JSON 顶层列表，并确认其中每一项都是对象。"""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CombineBuildError(f"{description}不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise CombineBuildError(f"{description}不是合法 JSON：{path}；{exc}") from exc

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CombineBuildError(f"{description}必须是由对象组成的 JSON 列表：{path}")
    return value


def require_nonempty_string(
    value: Any, field_name: str, record_label: str
) -> str:
    """读取记录中的非空字符串字段，并在缺失时给出可定位的错误。"""

    if not isinstance(value, str) or not value.strip():
        raise CombineBuildError(f"{record_label} 缺少非空字符串字段 {field_name}。")
    return value


def map_remote_path(
    remote_path: str,
    remote_root: str,
    local_root: Path,
    field_name: str,
    record_label: str,
) -> Path:
    """将受限远程绝对路径改写为项目内的本地资源路径。"""

    if not remote_path.startswith(remote_root):
        raise CombineBuildError(
            f"{record_label} 的 {field_name} 不在预期远程根目录下：{remote_path}"
        )

    relative_text = remote_path.removeprefix(remote_root)
    relative_path = PurePosixPath(relative_text)
    if not relative_text or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise CombineBuildError(f"{record_label} 的 {field_name} 包含不安全路径：{remote_path}")
    return local_root.joinpath(*relative_path.parts)


def collect_image_paths(record: dict[str, Any], record_label: str) -> list[str]:
    """读取题目图片路径，过滤空值、改写为本地路径并保持首次出现顺序。"""

    raw_paths = record.get("image_paths")
    if raw_paths is None or raw_paths == []:
        raw_paths = [record.get("image_path", "")]
    if not isinstance(raw_paths, list) or not all(isinstance(path, str) for path in raw_paths):
        raise CombineBuildError(f"{record_label} 的 image_paths 必须是字符串列表。")

    local_paths: list[str] = []
    for remote_path in raw_paths:
        if not remote_path:
            continue
        local_path = map_remote_path(
            remote_path,
            IMAGE_REMOTE_ROOT,
            IMAGE_LOCAL_ROOT,
            "image_path",
            record_label,
        )
        local_path_text = str(local_path)
        if local_path_text not in local_paths:
            local_paths.append(local_path_text)
    return local_paths


def load_ground_truths(
    record: dict[str, Any], record_label: str, cache: dict[Path, list[str]]
) -> list[str]:
    """读取 item_path 指向的 Ground Truth 文件并提取有序 claims。"""

    remote_item_path = require_nonempty_string(
        record.get("item_path"), "item_path", record_label
    )
    local_item_path = map_remote_path(
        remote_item_path,
        ITEM_REMOTE_ROOT,
        ITEM_LOCAL_ROOT,
        "item_path",
        record_label,
    )
    if local_item_path in cache:
        return cache[local_item_path]

    try:
        item_data = json.loads(local_item_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CombineBuildError(
            f"{record_label} 的 Ground Truth 文件不存在：{local_item_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CombineBuildError(
            f"{record_label} 的 Ground Truth 文件不是合法 JSON：{local_item_path}；{exc}"
        ) from exc

    try:
        claims = item_data["ready3_open_rewrite"]["claim_split"]["claims"]
    except (KeyError, TypeError) as exc:
        raise CombineBuildError(
            f"{record_label} 的 Ground Truth 文件缺少 "
            "ready3_open_rewrite.claim_split.claims。"
        ) from exc
    if not isinstance(claims, list):
        raise CombineBuildError(
            f"{record_label} 的 Ground Truth claims 必须是列表：{local_item_path}"
        )

    ground_truths = [
        require_nonempty_string(
            claim.get("claim") if isinstance(claim, dict) else None,
            "ready3_open_rewrite.claim_split.claims[].claim",
            record_label,
        )
        for claim in claims
    ]
    cache[local_item_path] = ground_truths
    return ground_truths


def build_source_records(
    dag_items: list[dict[str, Any]],
    source_items: list[dict[str, Any]],
    id_mode: IdMode,
) -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    """按指定 ID 规则将每条 DAG 与唯一来源记录配对。"""

    if id_mode == "source-order":
        if len(dag_items) != len(source_items):
            raise CombineBuildError(
                "顺序注入要求 dag.json 与原始记录 JSON 的条目数一致："
                f"{len(dag_items)} != {len(source_items)}。"
            )
        return [
            (dag_item, source_item, f"DAG 第 {index} 条")
            for index, (dag_item, source_item) in enumerate(
                zip(dag_items, source_items, strict=True), start=1
            )
        ]

    source_by_problem_id: dict[str, dict[str, Any]] = {}
    for index, source_item in enumerate(source_items, start=1):
        problem_id = require_nonempty_string(
            source_item.get("problem_id"), "problem_id", f"原始记录第 {index} 条"
        )
        if problem_id in source_by_problem_id:
            raise CombineBuildError(
                f"原始记录存在重复 problem_id，不能使用 problem-id 对齐：{problem_id}"
            )
        source_by_problem_id[problem_id] = source_item

    pairs: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for index, dag_item in enumerate(dag_items, start=1):
        original_batch_id = require_nonempty_string(
            dag_item.get("batch_id"), "batch_id", f"DAG 第 {index} 条"
        )
        source_item = source_by_problem_id.get(original_batch_id)
        if source_item is None:
            raise CombineBuildError(
                f"DAG 第 {index} 条的 batch_id 无法匹配来源 problem_id：{original_batch_id}"
            )
        pairs.append((dag_item, source_item, f"DAG 第 {index} 条（原 batch_id={original_batch_id}）"))
    return pairs


def build_combine_items(
    dag_items: list[dict[str, Any]],
    source_items: list[dict[str, Any]],
    id_mode: IdMode,
) -> list[dict[str, Any]]:
    """生成包含 sample_id、题目、Ground Truth、图片和图结构的输出条目。"""

    item_cache: dict[Path, list[str]] = {}
    output_items: list[dict[str, Any]] = []
    seen_batch_ids: set[str] = set()
    for dag_item, source_item, record_label in build_source_records(
        dag_items, source_items, id_mode
    ):
        sample_id = require_nonempty_string(
            source_item.get("sample_id"), "sample_id", record_label
        )
        if sample_id in seen_batch_ids:
            raise CombineBuildError(f"输出中出现重复 sample_id：{sample_id}")
        seen_batch_ids.add(sample_id)

        question = require_nonempty_string(source_item.get("question"), "question", record_label)
        graph = dag_item.get("graph")
        if not isinstance(graph, dict):
            raise CombineBuildError(f"{record_label} 的 DAG graph 必须是对象。")

        output_items.append(
            {
                "batch_id": sample_id,
                "problem_text": question,
                "ground_truths": load_ground_truths(source_item, record_label, item_cache),
                "image_paths": collect_image_paths(source_item, record_label),
                "graph": graph,
            }
        )
    return output_items


def write_json(output_path: Path, output_items: list[dict[str, Any]]) -> None:
    """以临时文件写出完整 JSON，并在成功后替换目标文件。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(output_path)


def execute(
    dag_path: Path, source_path: Path, output_path: Path, id_mode: IdMode
) -> int:
    """完成输入读取、对齐、资源组装、写出与结果统计。"""

    dag_items = load_json_list(dag_path, "dag.json")
    source_items = load_json_list(source_path, "原始记录 JSON")
    output_items = build_combine_items(dag_items, source_items, id_mode)
    write_json(output_path, output_items)
    print(f"已生成 {len(output_items)} 条 combine 记录：{output_path}")
    return 0


def main() -> int:
    """解析命令行参数，并将预期的数据错误转换为退出码 2。"""

    args = build_parser().parse_args()
    try:
        return execute(args.dag_json, args.source_json, args.output_json, args.id_mode)
    except CombineBuildError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
