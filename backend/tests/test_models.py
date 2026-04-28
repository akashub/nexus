from __future__ import annotations

from nexus.models import Concept, Conversation, Edge


class TestConceptFromRow:
    def test_minimal(self):
        c = Concept.from_row({"id": "1", "name": "React"})
        assert c.id == "1"
        assert c.name == "React"
        assert c.tags == []
        assert c.source == "manual"

    def test_with_tags_json(self):
        c = Concept.from_row({"id": "1", "name": "React", "tags": '["frontend","ui"]'})
        assert c.tags == ["frontend", "ui"]

    def test_with_tags_null(self):
        c = Concept.from_row({"id": "1", "name": "React", "tags": None})
        assert c.tags == []


class TestEdgeFromRow:
    def test_basic(self):
        e = Edge.from_row({
            "id": "1",
            "source_id": "a",
            "target_id": "b",
            "relationship": "uses",
        })
        assert e.relationship == "uses"
        assert e.weight == 1.0


class TestConversationFromRow:
    def test_with_related_concepts(self):
        c = Conversation.from_row({
            "id": "1",
            "question": "What is React?",
            "answer": "A UI library.",
            "related_concepts": '["a","b"]',
        })
        assert c.related_concepts == ["a", "b"]

    def test_null_related_concepts(self):
        c = Conversation.from_row({
            "id": "1",
            "question": "q",
            "answer": "a",
            "related_concepts": None,
        })
        assert c.related_concepts == []
