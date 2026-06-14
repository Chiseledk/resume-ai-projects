import json
import re
from typing import Optional

from pydantic import ValidationError

from backend.services.graph_algorithms import enrich_with_graph
from backend.utils.schema import MindMap


def parse_and_validate_mindmap(raw_json_str: str) -> Optional[MindMap]:
    """Parse model output, validate the semantic tree, then enrich it into graph data."""
    if not raw_json_str:
        print("[Data Parser] Empty model output.")
        return None

    try:
        data_dict = json.loads(_extract_json_object(raw_json_str))
        validated_mindmap = MindMap(**data_dict)
        return enrich_with_graph(validated_mindmap)
    except json.JSONDecodeError as exc:
        print(f"[Data Parser] JSON parse failed: {exc}")
        return None
    except ValidationError as exc:
        print(f"[Data Parser] Schema validation failed: {exc}")
        return None


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start:end + 1]
    return cleaned
