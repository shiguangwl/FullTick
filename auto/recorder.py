# recorder.py (修复版)
import json
import threading
import time

import pynput
from pynput.keyboard import Key
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Controller as MouseController

# --- 全局变量 ---
recorded_events = []
is_recording = False
last_event_time = None
SCRIPT_FILENAME = "mouse_script.json"

mouse = MouseController()

# 创建一个 Event 对象来同步停止
stop_event = threading.Event()

# 鼠标监听器（全局变量，在主程序中初始化）
mouse_listener = None


def start_recording():
    """开始录制"""
    global is_recording, last_event_time, recorded_events, mouse_listener
    if not is_recording:
        print("▶️  开始录制... 按 F10 停止。")
        is_recording = True
        recorded_events = []
        last_event_time = time.time()
        # 启动鼠标监听
        if mouse_listener and not mouse_listener.running:
            mouse_listener.start()


def stop_recording():
    """停止录制并保存"""
    global is_recording
    if is_recording:
        is_recording = False
        print("⏹️  录制停止。")
        # 停止鼠标监听
        # mouse_listener.stop() # 不再需要，由主线程统一处理
        save_script()


def save_script():
    """将录制的事件保存到文件"""
    if not recorded_events:
        print("没有录制任何事件。")
        return

    print(f"💾 正在保存脚本到 {SCRIPT_FILENAME}...")
    with open(SCRIPT_FILENAME, "w") as f:
        json.dump(recorded_events, f, indent=4)
    print("✅ 保存成功！")


def record_event(action, **kwargs):
    """记录一个事件，并计算与上一个事件的时间差"""
    global last_event_time
    if is_recording:
        current_time = time.time()
        time_since_last_event = current_time - last_event_time

        event_data = {"action": action, "time_since_last": time_since_last_event}
        event_data.update(kwargs)

        recorded_events.append(event_data)
        last_event_time = current_time


# --- 鼠标事件回调函数 ---
def on_move(x, y):
    record_event("move", x=x, y=y)


def on_click(x, y, button, pressed):
    action = "press" if pressed else "release"
    record_event("click", x=x, y=y, button=str(button), action_type=action)


def on_scroll(x, y, dx, dy):
    record_event("scroll", x=x, y=y, dx=dx, dy=dy)


# --- 键盘快捷键监听 ---
def on_key_press(key):
    try:
        if key == Key.f9 and not is_recording:
            start_recording()
        elif key == Key.f10 and is_recording:
            stop_recording()
            # 返回 False 停止键盘监听器线程
            return False
    except AttributeError:
        pass


# --- 主程序 ---
if __name__ == "__main__":
    print("--- 鼠标操作录制器 ---")
    print("用法:")
    print("  - 按 F9 开始录制")
    print("  - 按 F10 停止并保存")
    print("程序将在保存后自动退出。")

    # 初始化鼠标监听器
    mouse_listener = pynput.mouse.Listener(
        on_move=on_move, on_click=on_click, on_scroll=on_scroll
    )

    with KeyboardListener(on_press=on_key_press) as keyboard_listener:
        keyboard_listener.join()

    # 确保鼠标监听器也已停止
    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()

    print("程序已退出。")
