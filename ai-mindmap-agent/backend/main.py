import os

from flask import Flask, jsonify, render_template, request

from backend.services.mindmap_generator import generate_mindmap_content


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "mindmap-dev-secret")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/generate_mindmap", methods=["POST"])
def api_generate_mindmap():
    data = request.get_json(silent=True) or {}
    source_text = data.get("text", "").strip()

    if not source_text:
        return jsonify({
            "success": False,
            "error": "请输入源文本。",
            "generation_source": None,
        }), 400

    mindmap_object, error_message, generation_source, ai_status = generate_mindmap_content(source_text)
    if mindmap_object:
        mindmap_dict = mindmap_object.model_dump()
        return jsonify({
            "success": True,
            "mindmap": mindmap_dict,
            "mindmap_data": mindmap_object.model_dump_json(indent=2),
            "graph_data": mindmap_dict.get("graph"),
            "generation_source": generation_source,
            "ai_status": ai_status,
            "error": None,
        })

    return jsonify({
        "success": False,
        "mindmap": None,
        "mindmap_data": None,
        "graph_data": None,
        "generation_source": generation_source,
        "ai_status": ai_status,
        "error": error_message or "未知错误，无法生成思维导图。",
    }), 500


if __name__ == "__main__":
    app.run(debug=True)
