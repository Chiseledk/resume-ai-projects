import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
from config import MODEL_DIR

def save_voiceprint(username, feature):
    """保存声纹特征到本地"""
    path = os.path.join(MODEL_DIR, f"{username}.npy")
    np.save(path, feature)

def load_all_voiceprints():
    """加载所有已注册声纹"""
    users = {}
    for file in os.listdir(MODEL_DIR):
        if file.endswith(".npy"):
            name = file.replace(".npy", "")
            users[name] = np.load(os.path.join(MODEL_DIR, file))
    return users

def get_next_available_id():
    """获取下一个可用的数字ID"""
    users = load_all_voiceprints()
    if not users:
        return 1
    
    numeric_ids = []
    for name in users.keys():
        try:
            numeric_ids.append(int(name))
        except ValueError:
            continue
    
    if numeric_ids:
        return max(numeric_ids) + 1
    return 1

def find_match_user(input_feature, threshold):
    """在声纹库中查找匹配用户"""
    users = load_all_voiceprints()
    for name, feature in users.items():
        sim = cosine_similarity(input_feature, feature)[0][0]
        if sim >= threshold:
            return name, sim
    return None, 0