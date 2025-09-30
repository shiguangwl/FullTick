from pathlib import Path
from typing import override
import threading
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from data_handler import DataHandler
from logger import Logger


class FileMonitor(FileSystemEventHandler):
    def __init__(self, watch_directory: str, handler: DataHandler):
        super().__init__()
        # 监听目录
        self.watch_directory: Path = Path(watch_directory)
        # 当前监听的文件
        self.current_log_file: Path | None = None
        # 最后匹配成功的行号
        self.last_line_number: int = 0
        # 数据处理器
        self.handler: DataHandler = handler
        # 防抖相关
        self.debounce_timer: threading.Timer | None = None
        self.debounce_delay = 0.3
        self.pending_file_path: Path | None = None
        self.debounce_lock = threading.Lock()
        

    def get_latest_log_file(self) -> Path | None:
        """# 按文件名排序以获取最新的文件"""
        log_files = list(self.watch_directory.glob("XtClient_FormulaOutput_*.log"))
        if not log_files:
            return None
        return sorted(log_files, key=lambda f: f.name)[-1]
    
    
    def read_new_content(self, start_line_number: int, file_path: Path) -> int:
        """读取新内容，以空行为分隔符进行段落匹配"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # 从指定行号开始读取到文件末尾
            if start_line_number >= len(lines):
                return start_line_number

            # 将内容按空行分割成段落
            segments = self._split_into_segments(lines[start_line_number:])
            last_processed_line = start_line_number

            for segment_lines, segment_start_line in segments:
                segment_content = ''.join(segment_lines).strip()
                if segment_content:
                    actual_line_number = start_line_number + segment_start_line + 1
                    if self.handler.match(segment_content, file_path.name, actual_line_number):
                        # 更新游标到当前段落的结束位置
                        last_processed_line = start_line_number + segment_start_line + len(segment_lines)

            # 更新最后处理的行号
            self.last_line_number = last_processed_line
            return self.last_line_number

        except Exception as e:
            Logger.error(f"[{file_path}] 读取/处理文件时发生错误: {e}")
            return start_line_number

    def _split_into_segments(self, lines: list[str]) -> list[tuple[list[str], int]]:
        """将行列表按空行分割成段落

        Returns:
            list[tuple[list[str], int]]: 每个元组包含(段落行列表, 段落起始行号)
        """
        segments = []
        current_segment = []
        segment_start = 0

        for i, line in enumerate(lines):
            if line.strip() == '':  # 空行
                if current_segment:  # 如果当前段落不为空
                    segments.append((current_segment, segment_start))
                    current_segment = []
                # 更新下一个段落的起始位置
                segment_start = i + 1
            else:
                current_segment.append(line)

        # 处理最后一个段落
        if current_segment:
            segments.append((current_segment, segment_start))

        return segments

    def _debounced_process_file(self) -> None:
        """防抖后的文件处理"""
        with self.debounce_lock:
            if self.pending_file_path and self.pending_file_path == self.current_log_file:
                Logger.info(f"处理文件变更: {self.pending_file_path.name}")
                self.read_new_content(self.last_line_number, self.pending_file_path)
            self.debounce_timer = None
            self.pending_file_path = None

    @override
    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))
        # 确保修改的是当前正在监听的文件
        if self._is_target_file(file_path) and file_path == self.current_log_file:
            with self.debounce_lock:
                # 如果有正在等待的定时器，取消它
                if self.debounce_timer:
                    self.debounce_timer.cancel()

                # 设置新的定时器
                self.pending_file_path = file_path
                self.debounce_timer = threading.Timer(self.debounce_delay, self._debounced_process_file)
                self.debounce_timer.start()

    @override
    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        
        file_path = Path(str(event.src_path))
        if self._is_target_file(file_path):
            Logger.info(f"检测到新的日志文件: {file_path.name}")
            self.current_log_file = file_path
            self.last_line_number = 0
            self.read_new_content(self.last_line_number, file_path)
            
            
    def _is_target_file(self, file_path: Path) -> bool:
        return (file_path.name.startswith("XtClient_FormulaOutput_") and
                file_path.suffix == ".log")

    def start_monitoring(self) -> None:
        """开始监听文件变化"""
        if not self.watch_directory.exists():
            raise FileNotFoundError(f"监听目录不存在: {self.watch_directory}")
        
        self.current_log_file = self.get_latest_log_file()
        Logger.info(f"开始监听目录: {self.watch_directory}")
        # 如果当前有日志文件，先处理现有内容
        if self.current_log_file and self.current_log_file.exists():
            Logger.info(f"当前监听文件: {self.current_log_file.name}")
            self.read_new_content(0, self.current_log_file)
        else:
            Logger.warning("未找到日志文件，等待新文件创建...")

        observer = Observer()
        observer.schedule(self, str(self.watch_directory), recursive=False)
        observer.start()

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            Logger.info("接收到停止信号，正在关闭监听器...")
        except Exception as e:
            Logger.error(f"监听过程中出现异常: {e}")
        finally:
            # 清理防抖定时器
            with self.debounce_lock:
                if self.debounce_timer:
                    self.debounce_timer.cancel()
                    self.debounce_timer = None
            observer.stop()
            observer.join()
            Logger.info("监听器已停止")
