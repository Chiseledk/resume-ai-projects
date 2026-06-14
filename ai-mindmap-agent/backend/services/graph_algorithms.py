import math
import re
from collections import Counter
from typing import Dict, Iterable, List

try:
    import jieba.analyse
except ImportError:
    jieba = None

from backend.utils.schema import GraphEdge, GraphNode, MindMap, MindMapGraph, MindMapNode


_BULLET_RE = re.compile(r"^\s*(#{1,6}|[-*+]|[0-9]+[.)]|[一二三四五六七八九十]+[、.)])\s*")
_SENTENCE_SPLIT_RE = re.compile(r"[。！？!?；;]+")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_ENGLISH_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "your", "have",
    "一个", "一种", "以及", "可以", "通过", "进行", "这个", "这些", "需要", "我们",
    "它们", "他们", "为了", "因为", "所以", "如果", "但是", "然后", "其中",
    "强调", "系统", "负责", "介绍", "结合", "减少",
}
_DOMAIN_TERMS = [
    "思维导图", "图结构", "图算法", "段落主题", "关键词", "关键句", "段落聚类",
    "径向布局", "树布局", "层级布局", "可视化节点", "节点", "连线", "分支",
    "中心主题", "用户体验", "输入体验", "SVG", "JSON",
]

if jieba is not None:
    for _term in _DOMAIN_TERMS:
        jieba.add_word(_term, freq=20000)


def build_algorithmic_mindmap(source_text: str) -> MindMap:
    """Build a graph-ready mind map using NLP keyword extraction and tree layout."""
    title = _guess_title(source_text)
    structured_nodes = _parse_structured_lines(source_text)

    if _should_deepen_by_paragraph(source_text, structured_nodes):
        semantic_nodes = _parse_paragraph_keyword_tree(source_text)
    elif structured_nodes:
        semantic_nodes = _deepen_leaf_nodes_with_keywords(structured_nodes)
    else:
        semantic_nodes = _parse_paragraph_keyword_tree(source_text)

    mindmap = MindMap(title=title, nodes=semantic_nodes)
    mindmap.graph = build_graph(mindmap)
    return mindmap


def enrich_with_graph(mindmap: MindMap) -> MindMap:
    mindmap.graph = build_graph(mindmap)
    return mindmap


def build_graph(mindmap: MindMap) -> MindMapGraph:
    root_id = "root"
    nodes = [GraphNode(id=root_id, label=mindmap.title, depth=0, weight=3)]
    edges: List[GraphEdge] = []

    def walk(items: Iterable[MindMapNode], parent_id: str, depth: int, path: str) -> None:
        for index, item in enumerate(items):
            node_id = f"{path}-{index}"
            weight = max(1.0, 3.4 - depth * 0.45)
            nodes.append(GraphNode(
                id=node_id,
                label=item.name.strip()[:80],
                depth=depth,
                weight=weight,
                parent_id=parent_id,
            ))
            edges.append(GraphEdge(source=parent_id, target=node_id, weight=weight))
            if item.children:
                walk(item.children, node_id, depth + 1, node_id)

    walk(mindmap.nodes, root_id, 1, "n")
    _apply_radial_tidy_layout(nodes, edges)
    return MindMapGraph(nodes=nodes, edges=edges, layout="radial-tidy-tree")


def _parse_paragraph_keyword_tree(source_text: str) -> List[MindMapNode]:
    nodes: List[MindMapNode] = []
    for index, paragraph in enumerate(_split_paragraphs(source_text)[:8], start=1):
        sentences = _split_sentences(paragraph)
        keywords = _extract_keywords(paragraph, limit=4)
        keyword_nodes = []

        for keyword in keywords:
            related = _rank_sentences_for_keyword(sentences, keyword)
            details = [
                MindMapNode(name=_compact_sentence(sentence), children=None)
                for sentence in related[:2]
                if _compact_sentence(sentence) != keyword
            ]
            keyword_nodes.append(MindMapNode(name=keyword, children=details or None))

        if not keyword_nodes and sentences:
            keyword_nodes = [
                MindMapNode(name=_compact_sentence(sentence), children=None)
                for sentence in sentences[:3]
            ]

        nodes.append(MindMapNode(
            name=_paragraph_title(paragraph, keywords, index),
            children=keyword_nodes or None,
        ))
    return nodes


def _deepen_leaf_nodes_with_keywords(nodes: List[MindMapNode]) -> List[MindMapNode]:
    deepened: List[MindMapNode] = []
    for node in nodes:
        if node.children:
            deepened.append(MindMapNode(name=node.name, children=_deepen_leaf_nodes_with_keywords(node.children)))
            continue

        keywords = [keyword for keyword in _extract_keywords(node.name, limit=3) if keyword != node.name]
        if keywords and len(node.name) > 18:
            deepened.append(MindMapNode(
                name=_compact_sentence(node.name, limit=28),
                children=[MindMapNode(name=keyword, children=None) for keyword in keywords],
            ))
        else:
            deepened.append(node)
    return deepened


def _extract_keywords(text: str, limit: int = 5) -> List[str]:
    """Fuse TextRank, TF-IDF, and lightweight English frequency keywords."""
    scores: Counter[str] = Counter()

    for term in _DOMAIN_TERMS:
        hits = len(re.findall(re.escape(term), text, flags=re.IGNORECASE))
        if hits:
            scores[term] += hits * 120 + len(term)

    if jieba is not None and _CHINESE_RE.search(text):
        for keyword, weight in jieba.analyse.textrank(
            text,
            topK=limit * 4,
            withWeight=True,
            allowPOS=("n", "nr", "ns", "nt", "nz", "vn"),
        ):
            if _valid_keyword(keyword):
                scores[keyword] += weight * 100
        for keyword, weight in jieba.analyse.extract_tags(text, topK=limit * 3, withWeight=True):
            if _valid_keyword(keyword):
                scores[keyword] += weight * 10

    for word in _ENGLISH_WORD_RE.findall(text):
        normalized = word.upper() if word.isupper() else word.lower()
        if _valid_keyword(normalized):
            scores[normalized] += 10 + len(normalized)

    if not scores:
        scores.update(_fallback_ngram_keywords(text))

    return _dedupe_keywords([word for word, _ in scores.most_common()], limit)


def _fallback_ngram_keywords(text: str) -> Counter[str]:
    scores: Counter[str] = Counter()
    for block in re.findall(r"[\u4e00-\u9fff]+", text):
        for size in range(4, 1, -1):
            for index in range(max(0, len(block) - size + 1)):
                phrase = block[index:index + size]
                if _valid_keyword(phrase):
                    scores[phrase] += size
    return scores


def _valid_keyword(keyword: str) -> bool:
    cleaned = keyword.strip()
    if len(cleaned) < 2:
        return False
    if cleaned.lower() in _STOP_WORDS:
        return False
    if re.fullmatch(r"[\W_]+", cleaned):
        return False
    return True


def _dedupe_keywords(candidates: List[str], limit: int) -> List[str]:
    selected: List[str] = []
    for candidate in candidates:
        normalized = candidate.lower()
        if any(normalized == item.lower() for item in selected):
            continue
        if any(normalized in item.lower() or item.lower() in normalized for item in selected):
            continue
        if any(_has_strong_chinese_overlap(normalized, item.lower()) for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _rank_sentences_for_keyword(sentences: List[str], keyword: str) -> List[str]:
    if not sentences:
        return []

    keyword_lower = keyword.lower()
    scored = []
    for index, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        score = 0
        if keyword_lower in sentence_lower:
            score += 4
        score += len(set(_extract_keywords(sentence, limit=6)) & {keyword}) * 2
        score += max(0, 1.5 - index * 0.15)
        scored.append((score, sentence))

    return [sentence for _, sentence in sorted(scored, key=lambda item: item[0], reverse=True)]


def _apply_radial_tidy_layout(nodes: List[GraphNode], edges: List[GraphEdge]) -> None:
    node_by_id: Dict[str, GraphNode] = {node.id: node for node in nodes}
    children_by_parent: Dict[str, List[str]] = {}
    for edge in edges:
        children_by_parent.setdefault(edge.source, []).append(edge.target)

    leaf_order: Dict[str, int] = {}
    node_angle: Dict[str, float] = {}
    order = 0

    def assign_leaf_order(node_id: str) -> None:
        nonlocal order
        children = children_by_parent.get(node_id, [])
        if not children:
            leaf_order[node_id] = order
            order += 1
            return
        for child_id in children:
            assign_leaf_order(child_id)

    assign_leaf_order("root")
    leaf_total = max(1, order)

    def assign_angle(node_id: str) -> float:
        children = children_by_parent.get(node_id, [])
        if not children:
            angle = _angle_for_leaf(leaf_order[node_id], leaf_total)
        else:
            child_angles = [assign_angle(child_id) for child_id in children]
            angle = sum(child_angles) / len(child_angles)
        node_angle[node_id] = angle
        return angle

    assign_angle("root")

    for node in nodes:
        if node.id == "root":
            node.x = 0
            node.y = 0
            continue
        radius = 175 * node.depth
        angle = node_angle[node.id]
        node.x = round(math.cos(angle) * radius, 2)
        node.y = round(math.sin(angle) * radius, 2)


def _angle_for_leaf(index: int, total: int) -> float:
    if total == 1:
        return 0
    start = -math.pi * 0.92
    end = math.pi * 0.92
    return start + (end - start) * index / (total - 1)


def _should_deepen_by_paragraph(source_text: str, structured_nodes: List[MindMapNode]) -> bool:
    paragraphs = _split_paragraphs(source_text)
    return len(paragraphs) >= 2 or (not structured_nodes and len(source_text.strip()) > 80)


def _split_paragraphs(text: str) -> List[str]:
    chunks = _PARAGRAPH_SPLIT_RE.split(text.strip())
    if len(chunks) == 1:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) > 3 and not any(_line_level(line) is not None for line in lines):
            chunks = lines
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _split_sentences(paragraph: str) -> List[str]:
    normalized = re.sub(r"\s*\n\s*", "。", paragraph.strip())
    return [part.strip(" ，,：:") for part in _SENTENCE_SPLIT_RE.split(normalized) if part.strip()] or [paragraph.strip()]


def _paragraph_title(paragraph: str, keywords: List[str], index: int) -> str:
    first_line = _clean_line(paragraph.splitlines()[0])
    if len(first_line) <= 28:
        return first_line
    if keywords:
        return f"段落{index}：{keywords[0]}"
    return f"段落{index}"


def _guess_title(source_text: str) -> str:
    for line in source_text.splitlines():
        cleaned = _clean_line(line)
        if cleaned:
            return cleaned[:36]
    return "思维导图"


def _parse_structured_lines(source_text: str) -> List[MindMapNode]:
    roots: List[MindMapNode] = []
    stack: List[tuple[int, MindMapNode]] = []

    for raw_line in source_text.splitlines():
        if not raw_line.strip():
            continue
        level = _line_level(raw_line)
        text = _clean_line(raw_line)
        if not text:
            continue
        node = MindMapNode(name=text, children=[])

        if level is None:
            if stack:
                _append_child(stack[-1][1], node)
                stack.append((stack[-1][0] + 1, node))
            else:
                roots.append(node)
                stack.append((1, node))
            continue

        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            _append_child(stack[-1][1], node)
        else:
            roots.append(node)
        stack.append((level, node))

    return _trim_redundant_title(roots)


def _line_level(line: str) -> int | None:
    stripped = line.lstrip()
    indent_level = (len(line) - len(stripped)) // 2 + 1
    heading_match = re.match(r"^(#{1,6})\s+", stripped)
    if heading_match:
        return len(heading_match.group(1))
    bullet_match = re.match(r"^([-*+]|[0-9]+[.)]|[一二三四五六七八九十]+[、.)])\s*", stripped)
    if bullet_match:
        return indent_level + 1
    if re.match(r"^.{2,24}[:：]\s*\S+", stripped):
        return indent_level
    return None


def _clean_line(line: str) -> str:
    cleaned = _BULLET_RE.sub("", line.strip())
    cleaned = re.sub(r"^(.{2,24})[:：]\s*$", r"\1", cleaned)
    return cleaned.strip()


def _append_child(parent: MindMapNode, child: MindMapNode) -> None:
    if parent.children is None:
        parent.children = []
    parent.children.append(child)


def _trim_redundant_title(nodes: List[MindMapNode]) -> List[MindMapNode]:
    if len(nodes) == 1 and nodes[0].children:
        return nodes[0].children
    return nodes


def _has_strong_chinese_overlap(left: str, right: str) -> bool:
    if not (_is_chinese_text(left) and _is_chinese_text(right)):
        return False
    shorter = min(len(left), len(right))
    if shorter < 3:
        return False
    for size in range(shorter, 2, -1):
        left_parts = {left[index:index + size] for index in range(len(left) - size + 1)}
        right_parts = {right[index:index + size] for index in range(len(right) - size + 1)}
        if left_parts & right_parts:
            return True
    return False


def _is_chinese_text(text: str) -> bool:
    return bool(text) and all("\u4e00" <= char <= "\u9fff" for char in text)


def _compact_sentence(sentence: str, limit: int = 42) -> str:
    cleaned = _clean_line(sentence)
    return cleaned if len(cleaned) <= limit else f"{cleaned[:limit - 1]}..."
