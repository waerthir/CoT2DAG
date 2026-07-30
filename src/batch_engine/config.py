"""YAML 配置读取与校验。"""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


class ConfigError(ValueError):
    """YAML 配置文件缺失、格式错误或字段不合法时抛出的异常。"""


class PathsConfig(BaseModel):
    input_json: Path
    database: Path
    output_json: Path
    system_prompt: Path


class ModelConfig(BaseModel):
    litellm_model: str = Field(min_length=1)
    api_base: str = Field(min_length=1)
    api_key_env: str = Field(min_length=1)
    timeout_s: float = Field(gt=0)
    max_concurrency: int = Field(gt=0)
    completion_kwargs: dict[str, object] = Field(default_factory=dict)


class RetryConfig(BaseModel):
    max_attempts: int = Field(gt=0)
    min_wait_s: float = Field(gt=0)
    max_wait_s: float = Field(gt=0)
    retry_invalid_output: bool = True

    def model_post_init(self, __context: object) -> None:
        """在 Pydantic 创建配置对象后，检查退避时间上下限关系。"""
        if self.max_wait_s < self.min_wait_s:
            raise ValueError("retry.max_wait_s must be >= retry.min_wait_s")


class AppConfig(BaseModel):
    paths: PathsConfig
    model: ModelConfig
    retry: RetryConfig


def load_config(config_path: Path) -> AppConfig:
    """读取 YAML 配置、加载项目根目录 .env，并把路径转换为绝对路径。"""

    def get_project_root(marker_files=(".git", "pyproject.toml", ".env")) -> Path:
        """从当前文件出发，向上查找包含特征文件的目录作为项目根目录"""
        current_path = Path(__file__).resolve().parent
        for parent in [current_path] + list(current_path.parents):
            if any((parent / marker).exists() for marker in marker_files):
                return parent
        # 如果没找到，退回当前工作目录
        return Path.cwd()
    # 动态找到根目录
    project_root = get_project_root()
    # .env 不写入配置文件；运行时只从项目根目录加载它。
    load_dotenv(project_root / ".env")
    
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file does not exist: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Configuration root must be a mapping")

    try:
        config = AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc

    # YAML 中一般写相对路径，这里统一转换为绝对路径，后续模块无需关心当前工作目录。
    config.paths.input_json = _resolve_path(project_root, config.paths.input_json)
    config.paths.database = _resolve_path(project_root, config.paths.database)
    config.paths.output_json = _resolve_path(project_root, config.paths.output_json)
    config.paths.system_prompt = _resolve_path(project_root, config.paths.system_prompt)
    return config


def _resolve_path(project_root: Path, path: Path) -> Path:
    """将 YAML 中的相对路径拼接到项目根目录；绝对路径保持原样。"""
    return path if path.is_absolute() else project_root / path
