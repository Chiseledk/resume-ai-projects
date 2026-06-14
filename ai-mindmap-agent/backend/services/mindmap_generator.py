from typing import Literal, Optional, Tuple

from backend.services.ai_processor import generate_structured_mindmap, get_last_ai_error, optimize_mindmap_with_ai
from backend.services.data_parser import parse_and_validate_mindmap
from backend.services.graph_algorithms import build_algorithmic_mindmap
from backend.utils.schema import MindMap


GenerationSource = Literal["ai_optimized", "ai_direct", "algorithm_only"]
GenerationResult = Tuple[Optional[MindMap], Optional[str], Optional[GenerationSource], Optional[str]]


def generate_mindmap_content(source_text: str) -> GenerationResult:
    """Generate a mind map with deterministic algorithms, then refine it with AI when available."""
    print("\n--- Mind map generation started ---")

    draft_map = build_algorithmic_mindmap(source_text)
    if not (draft_map.nodes and draft_map.graph and draft_map.graph.nodes):
        return _generate_directly_with_ai(source_text)

    optimized_json = optimize_mindmap_with_ai(source_text, draft_map)
    if optimized_json:
        optimized_map = parse_and_validate_mindmap(optimized_json)
        if optimized_map:
            print("--- Algorithmic draft optimized by AI and graph layout regenerated ---")
            return optimized_map, None, "ai_optimized", "AI 优化成功"
        print("--- AI optimization could not be parsed; trying direct AI generation ---")
        direct_map, direct_error, direct_source, direct_status = _generate_directly_with_ai(source_text)
        if direct_map:
            return direct_map, direct_error, direct_source, "AI 优化解析失败，已改用 AI 直接生成"
        return draft_map, None, "algorithm_only", direct_status or "AI 已调用，但返回内容无法解析，已使用本地算法"

    print("--- Using algorithmic draft without AI optimization ---")
    ai_error = get_last_ai_error()
    if ai_error:
        return draft_map, None, "algorithm_only", f"AI 未返回可用结果：{ai_error}"
    return draft_map, None, "algorithm_only", "AI 未返回可用结果，已使用本地算法"


def _generate_directly_with_ai(source_text: str) -> GenerationResult:
    raw_json = generate_structured_mindmap(source_text)
    if raw_json:
        validated_map = parse_and_validate_mindmap(raw_json)
        if validated_map:
            print("--- AI mind map validated and graph layout generated ---")
            return validated_map, None, "ai_direct", "AI 直接生成成功"
        return None, "无法从 AI 返回内容中解析出可用的思维导图结构。", None, "AI 已调用，但返回内容无法解析"

    ai_error = get_last_ai_error()
    if ai_error:
        return None, "无法从输入文本中提取可用的思维导图结构。", None, f"AI 未返回可用结果：{ai_error}"
    return None, "无法从输入文本中提取可用的思维导图结构。", None, "AI 未返回可用结果"
