import time

try:
    from pinpong.board import Pin
    from config import BUZZER_PIN
    BUZZER_AVAILABLE = True
    buzzer = Pin(BUZZER_PIN, Pin.OUT)
except Exception as e:
    BUZZER_AVAILABLE = False
    print(f"[Feedback] 硬件未初始化 (Pinpong): {e}")


def beep_error():
    """错误提示音：哔一声"""
    if BUZZER_AVAILABLE:
        buzzer.write_digital(1)
        time.sleep(0.2)
        buzzer.write_digital(0)
    else:
        print("🔴 [模拟] 错误提示音: 哔一声")


def beep_success():
    """成功提示音：叮一声"""
    if BUZZER_AVAILABLE:
        buzzer.write_digital(1)
        time.sleep(0.1)
        buzzer.write_digital(0)
        time.sleep(0.05)
        buzzer.write_digital(1)
        time.sleep(0.15)
        buzzer.write_digital(0)
    else:
        print("🟢 [模拟] 成功提示音: 叮一声")


def flash_red():
    """失败反馈"""
    print("🔴 验证失败")


def flash_green():
    """成功反馈"""
    print("🟢 验证成功")