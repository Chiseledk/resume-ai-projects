import os

# ============================================================================
# 语音门禁系统 - Web版配置文件
# ============================================================================

# ==================== 管理员配置 ====================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")

# ==================== 千问 API 配置 ====================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# ==================== 语音配置 ====================
VOICE_COMMAND = "开门"
RECORD_SECONDS = 3
SAMPLE_RATE = 16000

# ==================== ASR 引擎配置 ====================
ASR_ENGINE = 'local'

# ==================== 声纹配置 ====================
VOICEPRINT_SIMILARITY_THRESHOLD = 0.85
DATA_DIR = "./data"
MODEL_DIR = os.path.join(DATA_DIR, "models")
RECORD_DIR = os.path.join(DATA_DIR, "records")

# ==================== 自动创建文件夹 ====================
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RECORD_DIR, exist_ok=True)
