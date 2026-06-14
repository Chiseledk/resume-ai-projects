import os
import sys

# 把当前目录加入路径（必须加，否则找不到模块）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from asr_web import _recognize_by_local

# 【你只需要改这里！】填入一段本地录音路径
TEST_AUDIO = "data/records/verify_1779627982.wav"  # 👈 改成你实际的录音文件

print("===== 开始单独测试本地口令+声纹识别 =====")
result_text, sim = _recognize_by_local(TEST_AUDIO)

print("\n===== 测试结果 =====")
print(f"返回文字：{result_text}")
print(f"相似度：{sim}")
print(f"是否包含‘开门’：{'开门' in result_text}")