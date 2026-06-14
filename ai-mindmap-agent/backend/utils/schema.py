from typing import List, Optional

from pydantic import BaseModel, Field


class MindMapNode(BaseModel):
    name: str
    children: Optional[List["MindMapNode"]] = None


class GraphNode(BaseModel):
    id: str
    label: str
    depth: int = 0
    x: float = 0
    y: float = 0
    weight: float = 1
    parent_id: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float = 1


class MindMapGraph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    layout: str = "radial-tidy-tree"


class MindMap(BaseModel):
    title: str
    nodes: List[MindMapNode]
    graph: Optional[MindMapGraph] = None
