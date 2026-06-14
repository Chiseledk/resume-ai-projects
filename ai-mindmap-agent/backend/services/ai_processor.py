import json
import os
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        return None

from backend.utils.schema import MindMap


def _load_project_env() -> None:
    """Load .env from project root even when python-dotenv is not installed."""
    load_dotenv()
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env()

SPARK_API_URL = os.getenv(
    "SPARK_API_URL",
    "https://spark-api-open.xf-yun.com/v1/chat/completions",
)
SPARK_API_PASSWORD = os.getenv("SPARK_API_PASSWORD") or os.getenv("SPARK_API_KEY")
SPARK_MODEL = os.getenv("SPARK_MODEL", "4.0Ultra")
MINDMAP_AI_ENABLED = os.getenv("MINDMAP_AI_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
LAST_AI_ERROR: Optional[str] = None


def get_last_ai_error() -> Optional[str]:
    return LAST_AI_ERROR


def generate_structured_mindmap(source_text: str) -> Optional[str]:
    """Call Spark API and request a strict tree-shaped mind-map JSON object."""
    system_prompt = f"""
你是一个思维导图生成专家。
请把用户文本转成严格 JSON。思维导图首先是一张图，但你只需要输出树形语义结构；
服务端会继续用图算法补充节点、边和布局坐标。

输出要求：
1. 只输出 JSON，不要 Markdown，不要解释文字。
2. title 是整张图的中心主题。
3. nodes 是一级分支，每个节点可继续包含 children。
4. 优先按“段落主题 -> 关键词 -> 关键句/支撑点”组织层级，让树至少有 3 层。
5. 节点名称要短、清晰、适合显示在图节点中。

JSON 必须符合以下 Schema：
{MindMap.model_json_schema()}
    """.strip()
    return _chat_json(system_prompt, source_text, temperature=0.1)


def optimize_mindmap_with_ai(source_text: str, draft_map: MindMap) -> Optional[str]:
    """Ask the model to refine an algorithmic draft without changing graph layout fields."""
    draft_json = json.dumps(
        draft_map.model_dump(exclude={"graph"}),
        ensure_ascii=False,
        indent=2,
    )
    system_prompt = f"""
你是一个思维导图结构优化专家。
你会收到用户原文和一个由算法生成的思维导图初稿。请在保留核心事实的前提下优化初稿。

优化目标：
1. 合并重复或过近的分支。
2. 把泛化词改成更具体、适合图节点显示的短标签。
3. 调整层级，让结构尽量呈现“段落主题 -> 关键词 -> 关键句/支撑点”。
4. 删除无意义节点，补足重要但遗漏的关键词。
5. 只输出语义树 JSON，不输出 graph、坐标、解释、Markdown。

JSON 必须符合以下 Schema：
{MindMap.model_json_schema()}
    """.strip()
    user_prompt = f"""
用户原文：
{source_text}

算法初稿：
{draft_json}

请输出优化后的 JSON。
    """.strip()
    return _chat_json(system_prompt, user_prompt, temperature=0.2)


def _chat_json(system_prompt: str, user_prompt: str, temperature: float) -> Optional[str]:
    global LAST_AI_ERROR
    LAST_AI_ERROR = None

    if not MINDMAP_AI_ENABLED:
        LAST_AI_ERROR = "AI 开关已关闭"
        print("[AI Processor] AI is disabled by MINDMAP_AI_ENABLED; local algorithm will be used.")
        return None

    if requests is None:
        LAST_AI_ERROR = "requests 依赖未安装"
        print("[AI Processor] requests is not installed; local algorithm will be used.")
        return None

    if not SPARK_API_PASSWORD:
        LAST_AI_ERROR = "SPARK_API_PASSWORD 未配置"
        print("[AI Processor] SPARK_API_PASSWORD is not configured; local algorithm will be used.")
        return None

    headers = {
        "Authorization": f"Bearer {SPARK_API_PASSWORD}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": SPARK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(SPARK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        LAST_AI_ERROR = str(exc)
        print(f"[AI Processor] Spark API call failed: {exc}")
        return None
