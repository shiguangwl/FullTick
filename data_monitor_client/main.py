#!/usr/bin/env python3

import datetime
from pathlib import Path
import sys
from data_handler import DataHandler
from file_monitor import FileMonitor
from logger import Logger

if __name__ == "__main__":
    # 从命令行参数获取监听目录，默认为当前目录
    watch_directory = sys.argv[1] if len(sys.argv) > 1 else "."

    Logger.info(f"监听目录: {Path(watch_directory).resolve()}")
    Logger.info("=" * 80)

    try:
        monitor = FileMonitor(watch_directory, DataHandler())
        monitor.start_monitoring()
    except Exception as e:
        Logger.error(f"程序异常退出: {e}")
        import traceback
        Logger.error(f"错误详情: {traceback.format_exc()}")
    finally:
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        Logger.info(f"程序结束时间: {end_time}")
