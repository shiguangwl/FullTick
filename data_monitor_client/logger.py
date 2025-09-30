
from datetime import datetime


class Logger:
    """日志记录器类"""

    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    @staticmethod
    def info(message: str) -> None:
        """输出信息级别日志"""
        print(f"[{Logger._get_timestamp()}] [INFO] {message}")

    @staticmethod
    def error(message: str) -> None:
        """输出错误级别日志"""
        print(f"[{Logger._get_timestamp()}] [ERROR] {message}")

    @staticmethod
    def warning(message: str) -> None:
        """输出警告级别日志"""
        print(f"[{Logger._get_timestamp()}] [WARNING] {message}")

