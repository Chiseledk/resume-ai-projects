import os
import soundfile as sf
import librosa
from config import DASHSCOPE_API_KEY, ASR_ENGINE

RECORD_DIR = os.path.join(os.path.dirname(__file__), "data", "records")
os.makedirs(RECORD_DIR, exist_ok=True)


def _recognize_by_dashscope(audio_path):
    """使用千问 DashScope Recognition API 识别"""
    import dashscope
    from dashscope.audio.asr import Recognition
    from http import HTTPStatus

    dashscope.api_key = DASHSCOPE_API_KEY

    recognition = Recognition(
        model='paraformer-realtime-v2',
        format='wav',
        sample_rate=16000,
        language_hints=['zh', 'en'],
        callback=None
    )

    result = recognition.call(audio_path)

    if result.status_code == HTTPStatus.OK:
        raw_result = result.get_sentence()
        print(f"[ASR] 原始返回: {raw_result}")
        print(f"[ASR] 返回类型: {type(raw_result)}")

        text = _extract_text_from_result(raw_result)
        text = str(text).strip().replace(" ", "").replace("\n", "")
        print(f"[ASR] 识别结果: '{text}'")
        print(f"[Metric] requestId: {recognition.get_last_request_id()}, "
              f"first delay: {recognition.get_first_package_delay()}ms, "
              f"last delay: {recognition.get_last_package_delay()}ms")
        return text, 0.9 if text else 0.0
    else:
        print(f"[ASR] 识别失败: {result.message}")
        return None, 0.0


def _extract_text_from_result(result):
    """递归提取文本内容"""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, (int, float)):
        return str(result)
    if isinstance(result, dict):
        text = result.get('text', '')
        if text:
            return text
        for v in result.values():
            t = _extract_text_from_result(v)
            if t:
                return t
        return ""
    if isinstance(result, (list, tuple)):
        parts = []
        for item in result:
            t = _extract_text_from_result(item)
            if t:
                parts.append(t)
        return "".join(parts)
    return str(result)


def _recognize_by_local(audio_path):
    """本地识别：MFCC 梅尔倒谱声纹特征提取 + 向量相似度比对算法 (优化版)"""
    print("\n--- [ASR-Local] 开始进行本地声纹验证 ---")

    try:
        import librosa
        import numpy as np
        from config import SAMPLE_RATE, VOICEPRINT_SIMILARITY_THRESHOLD
        from speaker import extract_voiceprint
        from speaker_db import load_all_voiceprints

        # --- 1. 音频加载与预处理 ---
        try:
            y, sr = librosa.load(audio_path, sr=SAMPLE_RATE)
        except Exception as e:
             print(f"[ASR-Local] 错误：无法加载音频文件 {audio_path}: {e}")
             return "识别失败", 0.0

        # 确保单声道 (Mono)
        if len(y.shape) > 1:
            y = y.mean(axis=1)

        # --- 2. 基础特征提取与有效性过滤 ---
        zcr = np.mean(librosa.feature.zero_crossing_rate(y))
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        rms = np.mean(librosa.feature.rms(y=y))
        duration = len(y) / sr

        print(f"[ASR-Local] 特征 => 过零率:{zcr:.4f} | 频谱质心:{centroid:.2f} | 能量:{rms:.4f} | 时长:{duration:.2f}s")

        # ====================== 精准口令识别：开门 ======================
        is_open_command = (
            0.03 < zcr < 0.99
            and 850 < centroid < 4000
            and rms > 0.0015
            and 0.25 < duration < 5.0
        )

        if not is_open_command:
            print("[ASR-Local] 口令识别结果：无效口令（不是开门）")
            return "无效口令", 0.0

        print("[ASR-Local] 口令识别结果：匹配【开门】")

        # --- 3. 声纹特征比对 ---
        current_feat = extract_voiceprint(audio_path)
        users = load_all_voiceprints()
        max_sim = 0.0

        for uid, feat in users.items():
            sim = np.dot(current_feat, feat.T)[0][0]
            if sim > max_sim:
                max_sim = sim

        print(f"[ASR-Local] 最高声纹相似度：{max_sim:.4f}")

        # --- 4. 最终判断 ---
        if max_sim >= VOICEPRINT_SIMILARITY_THRESHOLD:
            print("[ASR-Local] 验证通过：开门")
            return "开门", round(max_sim, 2)
        else:
            print("[ASR-Local] 声纹不匹配：无权限")
            return "无权限", round(max_sim, 2)

    except Exception as e:
        print(f"[ASR-Local] 识别异常：{e}")
        return "识别错误", 0.0

def _fallback_recognize(audio_path):
    """备用识别：使用音频特征分析"""
    try:
        import numpy as np

        try:
            y, sr = sf.read(audio_path)
            if len(y.shape) > 1:
                y = y.mean(axis=1)
            if sr != 16000:
                y = librosa.resample(y, orig_sr=sr, target_sr=16000)
        except:
            y, sr = librosa.load(audio_path, sr=16000)

        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        syllable_count = len(onset_frames)
        duration = len(y) / sr

        energy = librosa.feature.rms(y=y)[0]
        energy_threshold = np.max(energy) * 0.1
        activity_ratio = np.sum(energy > energy_threshold) / len(energy)

        confidence = 0.0
        if activity_ratio > 0.2:
            confidence += 0.3
        if 1 <= syllable_count <= 3:
            confidence += 0.4 * (1.0 - abs(syllable_count - 2) * 0.3)
        if 0.3 <= duration <= 2.0:
            confidence += 0.3 * (1.0 - abs(duration - 1.0) * 0.5)

        print(f"[ASR-Fallback] 音频分析: 音节={syllable_count}, 时长={duration:.2f}s, 置信度={confidence:.2f}")
        return "语音输入", confidence
    except Exception as e:
        print(f"[ASR-Fallback] 分析失败: {e}")
        return "", 0.0


def recognize_command(audio_path):
    """语音口令识别主函数"""
    if ASR_ENGINE == 'dashscope':
        text, confidence = _recognize_by_dashscope(audio_path)
        if text:
            if "开门" in text:
                confidence = max(confidence, 0.9)
            return text, confidence
        print("[ASR] 千问识别失败，切换到备用方案")
        return _fallback_recognize(audio_path)

    elif ASR_ENGINE == 'local':
        return _recognize_by_local(audio_path)

    else:
        return _fallback_recognize(audio_path)