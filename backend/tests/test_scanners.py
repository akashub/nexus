from __future__ import annotations

import json

import pytest

from nexus.scanners import is_valid_concept_name


class TestConceptNameValidation:
    @pytest.mark.parametrize("name", [
        "react", "fastapi", "playwright", "@tanstack/react-query",
        "drizzle-orm", "vue.js", "gh",
    ])
    def test_valid_names(self, name):
        assert is_valid_concept_name(name)

    @pytest.mark.parametrize("name", [
        "could", "yield", "or", "the", "similar", "just",
        "these", "strip", "track", "return", "import",
        "a", "2", "", "package1",
    ])
    def test_rejects_garbage(self, name):
        assert not is_valid_concept_name(name)

    def test_rejects_long_names(self):
        assert not is_valid_concept_name("x" * 61)

    def test_rejects_pure_numbers(self):
        assert not is_valid_concept_name("123")
        assert not is_valid_concept_name("42")

    def test_rejects_special_chars(self):
        assert not is_valid_concept_name("foo bar")
        assert not is_valid_concept_name("(test)")
        assert not is_valid_concept_name("$var")


class TestPackageScanner:
    def test_npm_scan(self, tmp_path):
        pkg = {"dependencies": {"react": "^18", "express": "^4"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        from nexus.scanners.packages import scan_npm
        result = scan_npm(tmp_path)
        names = {c.name for c in result.concepts}
        assert "react" in names
        assert "express" in names

    def test_npm_categories(self, tmp_path):
        pkg = {
            "dependencies": {"react": "^18", "express": "^4"},
            "devDependencies": {"eslint": "^9", "vitest": "^1"},
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        from nexus.scanners.packages import scan_npm
        result = scan_npm(tmp_path)
        cats = {c.name: c.category_hint for c in result.concepts}
        assert cats["react"] == "framework"
        assert cats["express"] == "framework"
        assert cats["eslint"] == "devtool"
        assert cats["vitest"] == "devtool"

    def test_npm_unknown_defaults_to_library(self, tmp_path):
        pkg = {"dependencies": {"some-random-lib": "^1"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        from nexus.scanners.packages import scan_npm
        result = scan_npm(tmp_path)
        assert result.concepts[0].category_hint == "library"

    def test_python_scan(self, tmp_path):
        toml = '[project]\nname = "myapp"\ndependencies = ["fastapi>=0.100", "httpx"]\n'
        (tmp_path / "pyproject.toml").write_text(toml)
        from nexus.scanners.packages import scan_python
        result = scan_python(tmp_path)
        names = {c.name for c in result.concepts}
        assert "fastapi" in names
        assert "httpx" in names
        assert "myapp" not in names

    def test_python_categories(self, tmp_path):
        toml = '[project]\nname = "x"\ndependencies = ["fastapi", "httpx", "ruff"]\n'
        (tmp_path / "pyproject.toml").write_text(toml)
        from nexus.scanners.packages import scan_python
        result = scan_python(tmp_path)
        cats = {c.name: c.category_hint for c in result.concepts}
        assert cats["fastapi"] == "framework"
        assert cats["httpx"] == "library"
        assert cats["ruff"] == "devtool"


class TestSyncValidation:
    def test_sync_rejects_garbage_names(self, tmp_path):
        from nexus.db import get_connection, init_db
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        from nexus.scanners import ScannedConcept, ScanResult
        from nexus.sync import sync_scan_results
        result = ScanResult(concepts=[
            ScannedConcept(name="react", source="eagle_mem"),
            ScannedConcept(name="could", source="eagle_mem"),
            ScannedConcept(name="the", source="eagle_mem"),
            ScannedConcept(name="2", source="eagle_mem"),
        ])
        stats = sync_scan_results(conn, str(tmp_path), result)
        assert stats["added"] == 1
        assert stats["skipped"] == 3
        conn.close()
