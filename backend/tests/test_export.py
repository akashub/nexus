from __future__ import annotations

from nexus.export import export_graph
from nexus.models import Concept, Edge


def _concept(name: str, **kw) -> Concept:
    defaults = {
        "id": name.lower(), "name": name,
        "source": "manual", "created_at": "", "updated_at": "",
    }
    return Concept(**{**defaults, **kw})


def _edge(src: str, tgt: str, rel: str = "uses") -> Edge:
    return Edge(id=f"{src}-{tgt}", source_id=src, target_id=tgt, relationship=rel, created_at="")


class TestExportJson:
    def test_basic(self):
        concepts = [_concept("React", category="framework", description="UI lib")]
        result = export_graph(concepts, [], fmt="json")
        assert result["concepts"][0]["name"] == "React"
        assert result["concepts"][0]["category"] == "framework"
        assert result["relationships"] == []

    def test_with_edges(self):
        concepts = [_concept("React"), _concept("JSX")]
        edges = [_edge("react", "jsx", "uses")]
        result = export_graph(concepts, edges, fmt="json")
        assert len(result["relationships"]) == 1
        assert result["relationships"][0]["source"] == "React"
        assert result["relationships"][0]["target"] == "JSX"


class TestExportMarkdown:
    def test_basic(self):
        concepts = [_concept(
            "React", category="framework",
            description="UI lib", summary="A UI library",
        )]
        md = export_graph(concepts, [], fmt="markdown")
        assert "## React (framework)" in md
        assert "*A UI library*" in md
        assert "UI lib" in md

    def test_with_connections(self):
        concepts = [_concept("React"), _concept("JSX")]
        edges = [_edge("react", "jsx", "uses")]
        md = export_graph(concepts, edges, fmt="markdown")
        assert "**uses** → JSX" in md

    def test_sorted_alphabetically(self):
        concepts = [_concept("Zod"), _concept("Axios")]
        md = export_graph(concepts, [], fmt="markdown")
        assert md.index("Axios") < md.index("Zod")
