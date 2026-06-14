import librosa
import numpy as np
import soundfile as sf
import io
from sklearn.metrics.pairwise import cosine_similarity
from config import SAMPLE_RATE

def extract_voiceprint(audio_path):
    """提取声纹特征（MFCC）"""
    filename = audio_path.lower()
    
    if filename.endswith('.webm'):
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path, format='webm')
            audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(1)
            y = np.array(audio.get_array_of_samples(), dtype=np.float32)
            y = y / (2**15)
            if len(y.shape) > 1:
                y = y.mean(axis=1)
        except:
            y, sr = _load_webm_fallback(audio_path)
    else:
        try:
            y, sr = sf.read(audio_path)
            if len(y.shape) > 1:
                y = y.mean(axis=1)
            if sr != SAMPLE_RATE:
                y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)
        except:
            y, sr = librosa.load(audio_path, sr=SAMPLE_RATE)
    
    mfcc = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1)
    return mfcc_mean.reshape(1, -1)


def _load_webm_fallback(audio_path):
    """使用 librosa 直接加载（需要 ffmpeg）"""
    return librosa.load(audio_path, sr=SAMPLE_RATE)

def compare_voiceprint(feature1, feature2):
    """计算两个声纹的相似度"""
    return cosine_similarity(feature1, feature2)[0][0]