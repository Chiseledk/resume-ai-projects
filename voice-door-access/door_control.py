import os

try:
    from pinpong.board import Pin
    from config import MOTOR_PIN
    MOTOR_AVAILABLE = True
    motor = Pin(MOTOR_PIN, Pin.OUT)
except Exception as e:
    MOTOR_AVAILABLE = False
    print(f"[DoorControl] 硬件未初始化 (Pinpong): {e}")

import time


def open_motor():
    """开电机（电风扇）"""
    if MOTOR_AVAILABLE:
        motor.write_digital(1)
        print("✅ 电机已启动（电风扇开启）")
    else:
        print("✅ [模拟] 电机已启动")


def close_motor():
    """关电机"""
    if MOTOR_AVAILABLE:
        motor.write_digital(0)
        print("🔒 电机已停止（电风扇关闭）")
    else:
        print("🔒 [模拟] 电机已停止")


def motor_action():
    """完整电机动作：开 → 延时5秒 → 关"""
    open_motor()
    time.sleep(5)
    close_motor()