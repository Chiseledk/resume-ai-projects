from flask import Flask, render_template, request, jsonify, session
import os
import time
import wave
import tempfile
import numpy as np

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_DIR = os.path.join(DATA_DIR, "models")
RECORD_DIR = os.path.join(DATA_DIR, "records")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RECORD_DIR, exist_ok=True)

from config import ADMIN_PASSWORD, VOICEPRINT_SIMILARITY_THRESHOLD

from speaker_db import (
    save_voiceprint, load_all_voiceprints, find_match_user, get_next_available_id
)
from speaker import extract_voiceprint
from asr_web import recognize_command


def clear_session_states():
    for key in list(session.keys()):
        if key not in ['admin_verified']:
            session.pop(key, None)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register")
def register_page():
    return render_template("register.html", next_id=get_next_available_id())


@app.route("/monitor")
def monitor_page():
    return render_template("monitor.html")


@app.route("/api/verify_admin", methods=["POST"])
def verify_admin():
    data = request.get_json()
    password = data.get("password", "")
    if password == ADMIN_PASSWORD:
        session["admin_verified"] = True
        return jsonify({"success": True, "next_id": get_next_available_id()})
    return jsonify({"success": False, "error": "密码错误"}), 401


@app.route("/api/check_admin")
def check_admin():
    verified = session.get("admin_verified", False)
    return jsonify({"verified": verified})


@app.route("/api/reset_admin")
def reset_admin():
    session.pop("admin_verified", None)
    return jsonify({"success": True})


def save_raw_audio(audio_file, output_dir, prefix="audio"):
    """保存原始音频文件 (前端已转为 WAV)"""
    audio_path = os.path.join(output_dir, f"{prefix}.wav")
    audio_file.seek(0)
    audio_file.save(audio_path)
    print(f"[AUDIO] 保存成功: {audio_path}")
    cleanup_old_records(output_dir, keep_count=3)
    return audio_path


def cleanup_old_records(directory, keep_count=3):
    """清理旧录音文件，只保留最新的 keep_count 个"""
    import glob
    
    all_files = glob.glob(os.path.join(directory, '*.wav'))
    
    if len(all_files) <= keep_count:
        return
    
    all_files.sort(key=os.path.getmtime, reverse=True)
    
    for old_file in all_files[keep_count:]:
        try:
            os.remove(old_file)
            print(f"[CLEANUP] 已删除旧录音: {old_file}")
        except Exception as e:
            print(f"[CLEANUP] 删除失败: {old_file}, {e}")


@app.route("/api/register_voice", methods=["POST"])
def register_voice():
    if not session.get("admin_verified", False):
        return jsonify({"success": False, "error": "未验证管理员身份"}), 403

    if "audio" not in request.files:
        return jsonify({"success": False, "error": "没有上传音频"}), 400

    audio_file = request.files["audio"]
    username = str(get_next_available_id())

    timestamp = str(int(time.time()))
    audio_path = save_raw_audio(audio_file, RECORD_DIR, f"reg_{username}_{timestamp}")

    try:
        feat = extract_voiceprint(audio_path)
        save_voiceprint(username, feat)

        recognized_text, cmd_conf = recognize_command(audio_path)

        return jsonify({
            "success": True,
            "user_id": username,
            "recognized_text": recognized_text,
            "confidence": cmd_conf
        })
    except Exception as e:
        import traceback
        print(f"[ERROR] 注册失败: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/verify_voice", methods=["POST"])
def verify_voice():
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "没有上传音频"}), 400

    audio_file = request.files["audio"]
    timestamp = str(int(time.time()))
    audio_path = save_raw_audio(audio_file, RECORD_DIR, f"verify_{timestamp}")

    try:
        feat = extract_voiceprint(audio_path)
        username, voice_sim = find_match_user(feat, VOICEPRINT_SIMILARITY_THRESHOLD)

        result = {
            "voiceprint_match": username is not None,
            "voiceprint_user_id": username,
            "voiceprint_similarity": round(voice_sim, 3) if voice_sim else 0
        }

        recognized_text, cmd_conf = recognize_command(audio_path)
        command_match = "开门" in recognized_text
        result["command_match"] = command_match
        result["command_text"] = recognized_text
        result["command_confidence"] = round(cmd_conf, 3) if cmd_conf else 0

        if username and command_match:
            result["access_granted"] = True
            result["message"] = f"验证成功：用户ID {username}，声纹相似度={voice_sim:.3f}，口令匹配"
            result["sound"] = "success"
        elif username and not command_match:
            result["access_granted"] = False
            result["message"] = f"声纹通过(相似度={voice_sim:.3f})，但口令错误"
            result["sound"] = "error"
        elif not username and command_match:
            result["access_granted"] = False
            result["message"] = f"口令正确，但声纹不匹配(相似度={voice_sim:.3f})"
            result["sound"] = "error"
        else:
            result["access_granted"] = False
            result["message"] = f"验证失败：声纹不匹配(相似度={voice_sim:.3f})，口令也错误"
            result["sound"] = "error"

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/users/count")
def users_count():
    users = load_all_voiceprints()
    return jsonify({"count": len(users), "users": list(users.keys())})


if __name__ == "__main__":
    print("=" * 50)
    print("语音门禁系统 - Web版")
    print("=" * 50)
    print(f"管理员密码: {ADMIN_PASSWORD}")
    print(f"数据目录: {DATA_DIR}")
    print(f"已注册用户: {len(load_all_voiceprints())}")
    print("=" * 50)
    print("启动服务: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
