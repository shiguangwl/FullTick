# main.py
import time
from datetime import datetime

import pygetwindow as gw
import schedule
import win32con
import win32gui

# 导入我们之前写好的回放功能
# 假设 player.py 和 main.py 在同一目录下
try:
    from player import playback_script
except ImportError:
    print(
        "❌ 错误：无法导入 playback_script。请确保 player.py 文件与 main.py 在同一目录下。"
    )
    exit()

WINDOW_TITLE_KEYWORD = "联储证券"


def find_and_focus_window(title_keyword):
    """
    查找标题包含指定关键字的窗口，并将其置顶激活。
    """
    try:
        # 使用 pygetwindow 查找窗口，它支持模糊匹配
        target_windows = gw.getWindowsWithTitle(title_keyword)
        if not target_windows:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🟡 未找到标题包含 '{title_keyword}' 的窗口。"
            )
            return False

        # 选择第一个匹配到的窗口
        window = target_windows[0]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 找到窗口: '{window.title}'")

        # 使用 win32gui 将窗口带到前台
        # 如果窗口最小化，先恢复
        if window.isMinimized:
            win32gui.ShowWindow(window._hWnd, win32con.SW_RESTORE)
            print(f"[{datetime.now().strftime('%H:%M:%S')}]   -> 窗口已恢复。")

        # 将窗口设为前台窗口
        win32gui.SetForegroundWindow(window._hWnd)
        print(f"[{datetime.now().strftime('%H:%M:%S')}]   -> 窗口已置顶。")
        time.sleep(1)  # 等待1秒确保窗口已完全激活
        return True

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 操作窗口时发生错误: {e}")
        return False


def run_scheduled_task():
    """
    这是一个组合任务：先置顶窗口，然后执行回放脚本。
    """
    print("\n" + "=" * 40)
    print("⏰ 到达预定时间，准备执行任务...")

    # 1. 查找并置顶窗口
    if find_and_focus_window(WINDOW_TITLE_KEYWORD):
        # 2. 如果窗口置顶成功，则执行鼠标回放
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 开始执行鼠标回放脚本...")
        try:
            playback_script(2.5)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 鼠标回放脚本执行完成。")
        except Exception as e:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 执行回放脚本时发生错误: {e}"
            )
    else:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 因未能找到或激活目标窗口，任务中断。"
        )
    print("=" * 40 + "\n")


def setup_schedule():
    """
    设置所有定时任务
    """
    print("--- 任务调度器已启动 ---")
    print(f"将在以下时间点，自动置顶 '{WINDOW_TITLE_KEYWORD}' 窗口并执行脚本：")

    # --- 设置上午的定时任务 ---
    # 固定时间点
    print("  - 上午 09:30 (固定)")
    schedule.every().day.at("09:30").do(run_scheduled_task)

    # 9:35 到 11:25 之间，每5分钟一次
    display_times = []
    for hour in range(9, 12):
        for minute in range(0, 60, 5):
            # 排除掉不在时间范围内的任务
            if (hour == 9 and minute < 35) or (hour == 11 and minute > 25):
                continue

            time_str = f"{hour:02d}:{minute:02d}"
            display_times.append(time_str)
            schedule.every().day.at(time_str).do(run_scheduled_task)
    print(f"  - 上午 {' 、'.join(display_times)}")

    print("  - 上午 11:30 (固定)")
    schedule.every().day.at("11:30").do(run_scheduled_task)

    # --- 设置下午的定时任务 ---
    # 固定时间点
    print("  - 下午 13:00 (固定)")
    schedule.every().day.at("13:00").do(run_scheduled_task)

    # 13:05 到 14:55 之间，每5分钟一次
    display_times = []
    for hour in range(13, 15):
        for minute in range(0, 60, 5):
            # 排除掉第一个5分钟（因为13:00已单独设置）
            if hour == 13 and minute == 0:
                continue

            time_str = f"{hour:02d}:{minute:02d}"
            display_times.append(time_str)
            schedule.every().day.at(time_str).do(run_scheduled_task)
    print(f"  - 下午 {' 、'.join(display_times)}")

    print("  - 下午 15:00 (固定)")
    schedule.every().day.at("15:00").do(run_scheduled_task)

    print("\n脚本正在后台运行，请勿关闭此窗口...")
    print("按 Ctrl+C 停止运行。")


if __name__ == "__main__":
    setup_schedule()

    # 启动时立即执行一次任务
    print("\n🚀 启动时立即执行一次任务...")
    run_scheduled_task()

    # 持续运行，等待任务触发
    while True:
        schedule.run_pending()
        time.sleep(1)
