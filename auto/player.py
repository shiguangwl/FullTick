# player.py (修复版)
import ctypes
import json
import sys
import time

from pynput.keyboard import Key
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Button
from pynput.mouse import Controller as MouseController

# 文件名
SCRIPT_FILENAME = "mouse_script.json"
mouse = MouseController()
# 添加一个锁，防止在回放时重复触发
is_playing = False
# 默认回放倍速
playback_speed = 1.0


def block_input(block=True):
    """
    阻止或恢复用户的键盘和鼠标输入

    参数:
        block (bool): True 为阻止输入, False 为恢复输入

    注意:
        - 仅在 Windows 系统上有效
        - 需要管理员权限
    """
    try:
        # 调用 Windows API BlockInput
        # 返回值: 成功返回非零值, 失败返回 0
        result = ctypes.windll.user32.BlockInput(block)
        if not result:
            if block:
                print("⚠️  警告: 无法阻止用户输入(可能需要管理员权限)")
            else:
                print("⚠️  警告: 无法恢复用户输入")
        return result
    except Exception as e:
        print(f"⚠️  警告: 调用 BlockInput 失败: {e}")
        return False


def get_button_from_string(button_str):
    """将字符串转换为 pynput 的 Button 对象"""
    if "left" in button_str:
        return Button.left
    elif "right" in button_str:
        return Button.right
    elif "middle" in button_str:
        return Button.middle
    return None


def playback_script(speed=1.0):
    """
    加载并回放脚本

    参数:
        speed (float): 回放倍速，默认为 1.0
                      - 1.0 = 正常速度
                      - 2.0 = 2倍速(更快)
                      - 0.5 = 0.5倍速(更慢)
    """
    global is_playing
    if is_playing:
        print("正在回放中，请勿重复触发。")
        return

    # 验证倍速参数
    if speed <= 0:
        print(f"❌ 错误：倍速参数必须大于 0，当前值: {speed}")
        return

    is_playing = True

    try:
        with open(SCRIPT_FILENAME, "r") as f:
            events = json.load(f)
    except FileNotFoundError:
        print(
            f"❌ 错误：找不到脚本文件 '{SCRIPT_FILENAME}'。请先运行 recorder.py 进行录制。"
        )
        is_playing = False
        return
    except json.JSONDecodeError:
        print(f"❌ 错误：脚本文件 '{SCRIPT_FILENAME}' 格式不正确。")
        is_playing = False
        return

    print(f"📖 脚本 '{SCRIPT_FILENAME}' 加载成功，包含 {len(events)} 个事件。")
    if speed != 1.0:
        print(f"⚡ 回放倍速: {speed}x")
    # print("3秒后开始回放，请将鼠标移动到安全位置...")
    time.sleep(1)
    print("🚀 回放开始！")

    # 阻止用户输入
    print("🔒 已阻止用户键盘和鼠标输入")
    block_input(True)

    try:
        for event in events:
            # 根据倍速调整等待时间
            time.sleep(event["time_since_last"] / speed)

            action = event["action"]

            if action == "move":
                mouse.position = (event["x"], event["y"])

            elif action == "click":
                button = get_button_from_string(event["button"])
                if button:
                    mouse.position = (event["x"], event["y"])
                    if event["action_type"] == "press":
                        mouse.press(button)
                    else:
                        mouse.release(button)

            elif action == "scroll":
                mouse.position = (event["x"], event["y"])
                mouse.scroll(event["dx"], event["dy"])

        print("✅ 回放完成！")
    finally:
        # 无论是否发生异常，都要恢复用户输入
        block_input(False)
        print("🔓 已恢复用户键盘和鼠标输入")
        is_playing = False


def on_key_press(key):
    """监听快捷键以启动回放"""
    global playback_speed
    try:
        if key == Key.f12:
            playback_script(speed=playback_speed)
            return False
    except AttributeError:
        pass


# --- 主程序 ---
if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        try:
            playback_speed = float(sys.argv[1])
            if playback_speed <= 0:
                print(f"❌ 错误：倍速参数必须大于 0，当前值: {playback_speed}")
                sys.exit(1)
        except ValueError:
            print(f"❌ 错误：无效的倍速参数 '{sys.argv[1]}'，请输入数字。")
            print("用法: python player.py [倍速]")
            print("示例: python player.py 2.0  # 2倍速回放")
            sys.exit(1)

    print("--- 鼠标操作回放器 ---")
    print("用法:")
    print(f"  - 确保 '{SCRIPT_FILENAME}' 文件存在。")
    print("  - 按 F12 开始回放。")
    if playback_speed != 1.0:
        print(f"  - 当前倍速: {playback_speed}x")
    print("程序将在回放结束后自动退出。")

    with KeyboardListener(on_press=on_key_press) as listener:
        listener.join()

    print("程序已退出。")
