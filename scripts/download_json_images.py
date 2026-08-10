"""从 JSON 中收集图片路径，并通过 SSH 别名镜像下载到本地。"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_ROOT = PROJECT_ROOT / "data" / "download" / "xAILab-public"
SSH_HOST_ALIAS = "xAILab-public"


class ImageDownloadInputError(ValueError):
    """输入 JSON 或远程图片路径不符合下载要求时抛出的异常。"""


def build_parser() -> argparse.ArgumentParser:
    """创建并返回图片下载脚本的命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="从 JSON 的 image_path 和 image_paths 字段下载图片。"
    )
    parser.add_argument("input_json", type=Path, help="输入 JSON 文件路径")
    return parser


def load_json(input_path: Path) -> Any:
    """读取并解析输入 JSON 文件。"""

    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ImageDownloadInputError(f"输入文件不存在：{input_path}") from exc
    except json.JSONDecodeError as exc:
        raise ImageDownloadInputError(f"输入文件不是合法 JSON：{exc}") from exc


def iter_image_paths(value: Any) -> Iterator[str]:
    """递归遍历 JSON 对象和列表，依次产出两个图片字段中的远程路径。"""

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "image_path":
                yield child
            elif key == "image_paths":
                yield from child
            else:
                yield from iter_image_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_image_paths(child)


def build_local_path(remote_path: str) -> Path:
    """将安全的远程绝对路径转换为下载根目录内的本地镜像路径。"""

    if not remote_path.startswith("/"):
        raise ImageDownloadInputError(f"远程图片路径必须是绝对路径：{remote_path}")
    if "\x00" in remote_path:
        raise ImageDownloadInputError("远程图片路径不能包含空字符。")

    posix_path = PurePosixPath(remote_path)
    parts = posix_path.parts[1:]
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ImageDownloadInputError(f"远程图片路径不安全：{remote_path}")

    local_path = DOWNLOAD_ROOT.joinpath(*parts)
    try:
        local_path.resolve().relative_to(DOWNLOAD_ROOT.resolve())
    except ValueError as exc:
        raise ImageDownloadInputError(f"远程图片路径超出下载目录：{remote_path}") from exc
    return local_path


def download_one(remote_path: str, local_path: Path) -> bool:
    """下载一张图片；目标文件已存在时返回 False，成功下载时返回 True。"""

    if local_path.is_file():
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = local_path.with_name(f".{local_path.name}.part")
    command = [
        "scp",
        f"{SSH_HOST_ALIAS}:{remote_path}",
        str(temporary_path),
    ]
    subprocess.run(command, check=True)
    temporary_path.replace(local_path)
    return True


def execute(input_path: Path) -> int:
    """收集、去重并逐张下载图片，最后输出下载统计和失败状态。"""

    source_data = load_json(input_path.resolve())
    image_paths = list(iter_image_paths(source_data))
    unique_paths = list(dict.fromkeys(image_paths))

    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    for remote_path in unique_paths:
        try:
            local_path = build_local_path(remote_path)
            if download_one(remote_path, local_path):
                downloaded_count += 1
                print(f"已下载：{remote_path}")
            else:
                skipped_count += 1
                print(f"已跳过：{remote_path}")
        except (ImageDownloadInputError, OSError, subprocess.CalledProcessError) as exc:
            failed_count += 1
            print(f"下载失败：{remote_path}\n  原因：{exc}")

    print(
        "统计："
        f"发现路径={len(image_paths)}，"
        f"去重后路径={len(unique_paths)}，"
        f"已下载={downloaded_count}，"
        f"已跳过={skipped_count}，"
        f"失败={failed_count}"
    )
    return 1 if failed_count else 0


def main() -> int:
    """解析命令行参数并运行下载流程。"""

    args = build_parser().parse_args()
    try:
        return execute(args.input_json)
    except ImageDownloadInputError as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
