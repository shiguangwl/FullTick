from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# 配置日志
logger = logging.getLogger(__name__)


class DataPersistence:
    """数据持久化服务, 负责数据的保存、加载和自动保存功能."""

    def __init__(self, data_file_path: str = "data_record.json") -> None:
        self.data_file_path = Path(data_file_path)
        self.lock = threading.Lock()
        self.auto_save_thread: threading.Thread | None = None
        self.stop_auto_save = False

    def save_data(self, data_list: list[dict[str, Any]]) -> bool:
        """保存数据到JSON文件."""
        try:
            with self.lock:
                # 确保目录存在
                self.data_file_path.parent.mkdir(parents=True, exist_ok=True)

                with self.data_file_path.open("w", encoding="utf-8") as f:
                    json.dump(data_list, f, ensure_ascii=False, indent=2)
                logger.info("数据已保存到 %s, 共 %d 条记录", self.data_file_path, len(data_list))
                return True
        except Exception:
            logger.exception("保存数据失败")
            return False

    def load_data(self) -> list[dict[str, Any]]:
        """从JSON文件加载数据."""
        if not self.data_file_path.exists():
            logger.warning("数据文件不存在: %s, 将从空数据开始", self.data_file_path)
            return []

        try:
            with self.data_file_path.open("r", encoding="utf-8") as f:
                data_list: list[dict[str, Any]] = json.load(f)

            logger.info("从 %s 加载了 %d 条记录", self.data_file_path, len(data_list))
        except Exception:
            logger.exception("加载数据失败")
            return []
        else:
            return data_list

    def start_auto_save(self, get_data_callback: Callable[[], list[dict[str, Any]]], interval: int = 300) -> None:
        """启动自动保存线程.

        Args:
            get_data_callback: 获取数据的回调函数
            interval: 保存间隔(秒)
        """
        if self.auto_save_thread is not None:
            logger.warning("自动保存线程已经在运行")
            return

        self.stop_auto_save = False
        self.auto_save_thread = threading.Thread(
            target=self._auto_save_worker,
            args=(get_data_callback, interval),
            daemon=True,
            name="DataPersistence-AutoSave",
        )
        self.auto_save_thread.start()
        logger.info("自动保存线程已启动, 间隔 %d 秒", interval)

    def _auto_save_worker(self, get_data_callback: Callable[[], list[dict[str, Any]]], interval: int) -> None:
        """自动保存工作线程."""
        while not self.stop_auto_save:
            try:
                time.sleep(interval)
                if not self.stop_auto_save:
                    data_list = get_data_callback()
                    if data_list:
                        self.save_data(data_list)
            except Exception:
                logger.exception("自动保存异常")

    def stop_auto_save_thread(self) -> None:
        """停止自动保存线程."""
        if self.auto_save_thread is None:
            return

        self.stop_auto_save = True
        if self.auto_save_thread.is_alive():
            self.auto_save_thread.join(timeout=5)

        self.auto_save_thread = None
        logger.info("自动保存线程已停止")
