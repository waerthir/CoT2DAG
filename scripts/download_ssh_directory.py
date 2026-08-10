"""通过 SSH/SFTP 递归镜像远程目录到本地目录。"""

from __future__ import annotations

import argparse
import getpass
import logging
import posixpath
import stat
from dataclasses import dataclass
from pathlib import Path

import paramiko
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


SSH_HOST_ALIAS = "xAILab-public"
SSH_CONFIG_PATH = Path.home() / ".ssh" / "config"
RETRYABLE_EXCEPTIONS = (OSError, EOFError, paramiko.SSHException)


class DirectoryDownloadError(RuntimeError):
    """SSH 配置、远程目录或本地目标目录不能正常处理时抛出的异常。"""


@dataclass
class DownloadStats:
    """记录目录镜像过程中的目录、文件和失败数量。"""

    directories: int = 0
    files: int = 0
    skipped: int = 0
    downloaded: int = 0
    failed: int = 0


def build_parser() -> argparse.ArgumentParser:
    """创建并返回目录下载器的命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="通过 SSH/SFTP 递归下载远程目录。")
    parser.add_argument("remote_directory", help="远程源目录的绝对路径")
    parser.add_argument("local_directory", type=Path, help="本地下载目录路径")
    return parser


def load_ssh_host_config() -> dict[str, object]:
    """从用户 SSH 配置读取 xAILab-public 的连接参数。"""

    if not SSH_CONFIG_PATH.is_file():
        raise DirectoryDownloadError(f"SSH 配置文件不存在：{SSH_CONFIG_PATH}")

    ssh_config = paramiko.SSHConfig()
    with SSH_CONFIG_PATH.open(encoding="utf-8") as config_file:
        ssh_config.parse(config_file)
    host_config = ssh_config.lookup(SSH_HOST_ALIAS)

    hostname = host_config.get("hostname")
    if not isinstance(hostname, str) or not hostname:
        raise DirectoryDownloadError(
            f"SSH 配置中未找到主机别名 {SSH_HOST_ALIAS} 的 HostName。"
        )
    return host_config


class SftpConnection:
    """管理一个可在断线后重新建立的 SSH/SFTP 长连接。"""

    def __init__(self) -> None:
        """读取 SSH 配置并初始化尚未连接的客户端状态。"""

        self._host_config = load_ssh_host_config()
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    @property
    def sftp(self) -> paramiko.SFTPClient:
        """返回当前可用的 SFTP 客户端；未连接时建立连接。"""

        if self._sftp is None:
            self.connect()
        assert self._sftp is not None
        return self._sftp

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def connect(self) -> None:
        """按 SSH 配置建立客户端和 SFTP 会话，失败时自动重试。"""

        self.close()
        hostname = str(self._host_config["hostname"])
        username = str(self._host_config.get("user") or getpass.getuser())
        port = int(self._host_config.get("port") or 22)
        identity_files = self._host_config.get("identityfile", [])
        key_filenames = [str(item) for item in identity_files]

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            hostname=hostname,
            port=port,
            username=username,
            key_filename=key_filenames or None,
            look_for_keys=not key_filenames,
            allow_agent=True,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        self._client = client
        self._sftp = client.open_sftp()

    def reconnect(self) -> None:
        """关闭失效连接并重新建立 SFTP 会话。"""

        self.close()
        self.connect()

    def close(self) -> None:
        """关闭当前 SFTP 与 SSH 客户端；未连接时安全返回。"""

        if self._sftp is not None:
            self._sftp.close()
            self._sftp = None
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> SftpConnection:
        """进入上下文时建立首个 SFTP 连接。"""

        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        """离开上下文时关闭连接。"""

        self.close()


class DirectoryDownloader:
    """递归下载远程目录，并通过文件大小判断是否需要补传。"""

    def __init__(self, connection: SftpConnection) -> None:
        """保存共享 SFTP 连接和本次下载统计。"""

        self._connection = connection
        self.stats = DownloadStats()

    def _recover_connection(self) -> None:
        """在可恢复的 SFTP 异常后重建连接。"""

        self._connection.reconnect()

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _list_directory(self, remote_directory: str) -> list[paramiko.SFTPAttributes]:
        """读取远程目录条目；连接故障后重连并重试。"""

        try:
            return self._connection.sftp.listdir_attr(remote_directory)
        except RETRYABLE_EXCEPTIONS:
            self._recover_connection()
            raise

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _stat_file(self, remote_path: str) -> paramiko.SFTPAttributes:
        """读取远程文件当前属性；连接故障后重连并重试。"""

        try:
            return self._connection.sftp.stat(remote_path)
        except RETRYABLE_EXCEPTIONS:
            self._recover_connection()
            raise

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _download_file(self, remote_path: str, temporary_path: Path) -> None:
        """把单个远程文件写入临时文件；连接故障后重连并重试。"""

        try:
            self._connection.sftp.get(remote_path, str(temporary_path))
        except RETRYABLE_EXCEPTIONS:
            self._recover_connection()
            raise

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS + (DirectoryDownloadError,)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _download_and_verify(
        self, remote_path: str, temporary_path: Path, remote_size: int
    ) -> None:
        """下载临时文件并校验大小；大小不符时重新传输。"""

        self._download_file(remote_path, temporary_path)
        temporary_size = temporary_path.stat().st_size
        if temporary_size != remote_size:
            raise DirectoryDownloadError(
                f"文件大小不一致：远端={remote_size}，临时文件={temporary_size}，"
                f"路径={remote_path}"
            )

    def _mirror_file(self, remote_path: str, local_path: Path) -> None:
        """按远端大小跳过完整文件，或下载、校验并替换目标文件。"""

        self.stats.files += 1
        try:
            remote_size = self._stat_file(remote_path).st_size
            if local_path.is_file() and local_path.stat().st_size == remote_size:
                self.stats.skipped += 1
                return

            local_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = local_path.with_name(f".{local_path.name}.part")
            self._download_and_verify(remote_path, temporary_path, remote_size)
            temporary_path.replace(local_path)
            self.stats.downloaded += 1
            print(f"已下载：{remote_path}")
        except (DirectoryDownloadError, OSError, paramiko.SSHException) as exc:
            self.stats.failed += 1
            print(f"下载失败：{remote_path}\n  原因：{exc}")

    def mirror_directory(self, remote_directory: str, local_directory: Path) -> None:
        """递归镜像一个远程目录，并让单文件失败不阻塞其他条目。"""

        try:
            entries = self._list_directory(remote_directory)
        except (OSError, EOFError, paramiko.SSHException) as exc:
            self.stats.failed += 1
            print(f"目录读取失败：{remote_directory}\n  原因：{exc}")
            return

        local_directory.mkdir(parents=True, exist_ok=True)
        self.stats.directories += 1
        for entry in entries:
            entry_name = entry.filename
            if entry_name in {".", ".."}:
                continue
            remote_child = posixpath.join(remote_directory, entry_name)
            local_child = local_directory / entry_name
            if stat.S_ISDIR(entry.st_mode):
                self.mirror_directory(remote_child, local_child)
            else:
                self._mirror_file(remote_child, local_child)


def validate_arguments(remote_directory: str, local_directory: Path) -> tuple[str, Path]:
    """检查远程源目录与本地下载目录的基本形式。"""

    if not remote_directory.startswith("/"):
        raise DirectoryDownloadError("远程源目录必须是绝对路径。")
    if "\x00" in remote_directory:
        raise DirectoryDownloadError("远程源目录不能包含空字符。")
    return remote_directory.rstrip("/") or "/", local_directory


def execute(remote_directory: str, local_directory: Path) -> int:
    """完成目录镜像下载，并输出本次传输统计。"""

    remote_directory, local_directory = validate_arguments(
        remote_directory, local_directory
    )
    with SftpConnection() as connection:
        downloader = DirectoryDownloader(connection)
        downloader.mirror_directory(remote_directory, local_directory)

    stats = downloader.stats
    print(
        "统计："
        f"目录={stats.directories}，文件={stats.files}，"
        f"已跳过={stats.skipped}，已下载={stats.downloaded}，失败={stats.failed}"
    )
    return 1 if stats.failed else 0


def main() -> int:
    """解析命令行参数并运行目录下载器。"""

    args = build_parser().parse_args()
    try:
        return execute(args.remote_directory, args.local_directory)
    except (DirectoryDownloadError, OSError, EOFError, paramiko.SSHException) as exc:
        print(f"错误：{exc}")
        return 2


if __name__ == "__main__":
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    raise SystemExit(main())
