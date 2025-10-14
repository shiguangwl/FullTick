"""应用配置管理."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """应用配置."""

    # 服务器配置
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 5000
    debug: bool = True

    # API配置
    api_secret_key: str = "123456"  # noqa: S105

    # 数据持久化配置
    data_file_path: str = "data_record.json"
    auto_save_interval: int = 10

    # 股票名称API配置
    stock_api_timeout: int = 5
    stock_api_max_workers: int = 3

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def from_env(cls) -> AppConfig:
        """从环境变量创建配置."""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),  # noqa: S104
            port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("DEBUG", "true").lower() == "true",
            api_secret_key=os.getenv("API_SECRET_KEY", "123456"),
            data_file_path=os.getenv("DATA_FILE_PATH", "data_record.json"),
            auto_save_interval=int(os.getenv("AUTO_SAVE_INTERVAL", "300")),
            stock_api_timeout=int(os.getenv("STOCK_API_TIMEOUT", "5")),
            stock_api_max_workers=int(os.getenv("STOCK_API_MAX_WORKERS", "3")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def setup_logging(config: AppConfig) -> None:
    """设置日志配置."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path("logs") / "app.log", encoding="utf-8"),
        ],
    )

    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)


# 全局配置实例
config = AppConfig.from_env()
