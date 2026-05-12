from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "about", "between",
    "through", "and", "but", "or", "not", "no", "so", "if", "then",
    "than", "how", "what", "which", "who", "this", "that", "it", "its",
    "my", "your", "i", "you", "he", "she", "we", "they", "me", "him",
    "us", "them", "why", "when", "where", "also", "just", "only", "very",
    "too", "each", "every", "all", "any", "few", "more", "most", "some",
    "such", "other", "new", "old", "up", "out", "off", "over", "under",
    "again", "once", "here", "there", "now", "still", "already", "yet",
    "similar", "using", "used", "use", "set", "get", "run", "make",
    "like", "need", "want", "try", "see", "know", "take", "give",
    "find", "tell", "ask", "work", "call", "keep", "let", "put",
    "say", "go", "come", "think", "look", "turn", "start", "show",
    "add", "fix", "update", "remove", "delete", "create", "build",
    "test", "check", "move", "change", "read", "write", "send",
    "yield", "return", "import", "export", "class", "def", "var", "next",
    "strip", "split", "join", "sort", "map", "filter", "reduce", "track",
    "const", "true", "false", "null", "none", "yes", "ok",
    "these", "those", "their", "our", "done", "made",
    "after", "before", "above", "below", "both", "same", "own",
    "back", "well", "way", "even", "much", "many", "must",
    "file", "line", "code", "data", "type", "name", "path",
    "note", "step", "case", "time", "part", "list", "item",
    "first", "last", "long", "short", "full", "half",
    "high", "low", "left", "right", "top", "end", "big", "small",
    "good", "bad", "best", "real", "sure", "able", "key", "value",
    "package1",
})

_VALID_NAME_RE = re.compile(r"^[@a-zA-Z][\w./@-]*$")


def is_valid_concept_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 60:
        return False
    if name.isdigit():
        return False
    if name.lower() in _STOPWORDS:
        return False
    return bool(_VALID_NAME_RE.match(name))


@dataclass
class ScannedConcept:
    name: str
    source: str
    category_hint: str | None = None
    context: str | None = None
    is_dev_dep: bool = False
    setup_command: str | None = None


@dataclass
class ScannedRelationship:
    source_name: str
    target_name: str
    relationship: str
    reason: str | None = None


@dataclass
class ScanResult:
    concepts: list[ScannedConcept] = field(default_factory=list)
    relationships: list[ScannedRelationship] = field(default_factory=list)
    project_description: str | None = None

    def merge(self, other: ScanResult) -> None:
        seen = {c.name.lower() for c in self.concepts}
        for c in other.concepts:
            if c.name.lower() not in seen:
                self.concepts.append(c)
                seen.add(c.name.lower())
        self.relationships.extend(other.relationships)
        if other.project_description and not self.project_description:
            self.project_description = other.project_description
