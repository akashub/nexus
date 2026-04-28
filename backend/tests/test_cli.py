from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from nexus.cli import main
from nexus.db import get_connection, init_db


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture()
def runner(db_path: Path):
    init_db(db_path)
    with patch("nexus.cli.get_connection", lambda: get_connection(db_path)):
        yield CliRunner()


def invoke(runner: CliRunner, args: list[str]):
    return runner.invoke(main, args, catch_exceptions=False)


class TestDbInit:
    def test_init(self, runner):
        result = invoke(runner, ["db", "init"])
        assert result.exit_code == 0
        assert "Database initialized" in result.output


class TestAdd:
    def test_add_basic(self, runner):
        result = invoke(runner, ["add", "React", "--no-enrich"])
        assert result.exit_code == 0
        assert "Added: React" in result.output

    def test_add_with_options(self, runner):
        result = invoke(runner, [
            "add", "Claude Code",
            "-c", "devtool",
            "-t", "cli,agent",
            "-n", "Main tool",
            "--no-enrich",
        ])
        assert result.exit_code == 0
        assert "Added: Claude Code" in result.output

    def test_add_duplicate(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        result = runner.invoke(main, ["add", "React", "--no-enrich"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestList:
    def test_list_empty(self, runner):
        result = invoke(runner, ["list"])
        assert "No concepts yet" in result.output

    def test_list_with_concepts(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        invoke(runner, ["add", "Vue", "--no-enrich"])
        result = invoke(runner, ["list"])
        assert "React" in result.output
        assert "Vue" in result.output

    def test_list_category_filter(self, runner):
        invoke(runner, ["add", "React", "-c", "framework", "--no-enrich"])
        invoke(runner, ["add", "SQLite", "-c", "concept", "--no-enrich"])
        result = invoke(runner, ["list", "-c", "framework"])
        assert "React" in result.output
        assert "SQLite" not in result.output

    def test_list_json(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        result = invoke(runner, ["list", "--format", "json"])
        assert '"name": "React"' in result.output


class TestConnect:
    def test_connect(self, runner):
        invoke(runner, ["add", "A", "--no-enrich"])
        invoke(runner, ["add", "B", "--no-enrich"])
        result = invoke(runner, ["connect", "A", "B", "-t", "uses"])
        assert "Connected: A --[uses]--> B" in result.output

    def test_connect_missing_concept(self, runner):
        invoke(runner, ["add", "A", "--no-enrich"])
        result = runner.invoke(main, ["connect", "A", "Missing"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_connect_default_type(self, runner):
        invoke(runner, ["add", "A", "--no-enrich"])
        invoke(runner, ["add", "B", "--no-enrich"])
        result = invoke(runner, ["connect", "A", "B"])
        assert "related_to" in result.output


class TestSearch:
    def test_search_found(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        result = invoke(runner, ["search", "React"])
        assert "React" in result.output
        assert "1 result" in result.output

    def test_search_not_found(self, runner):
        result = invoke(runner, ["search", "nonexistent"])
        assert "No results" in result.output


class TestShow:
    def test_show_basic(self, runner):
        invoke(runner, ["add", "React", "-c", "framework", "-t", "ui,frontend", "--no-enrich"])
        result = invoke(runner, ["show", "React"])
        assert "React" in result.output
        assert "framework" in result.output
        assert "ui" in result.output

    def test_show_with_edges(self, runner):
        invoke(runner, ["add", "A", "--no-enrich"])
        invoke(runner, ["add", "B", "--no-enrich"])
        invoke(runner, ["connect", "A", "B", "-t", "uses"])
        result = invoke(runner, ["show", "A"])
        assert "Outgoing:" in result.output
        assert "-> B" in result.output

    def test_show_incoming(self, runner):
        invoke(runner, ["add", "A", "--no-enrich"])
        invoke(runner, ["add", "B", "--no-enrich"])
        invoke(runner, ["connect", "A", "B", "-t", "uses"])
        result = invoke(runner, ["show", "B"])
        assert "Incoming:" in result.output
        assert "<- A" in result.output

    def test_show_not_found(self, runner):
        result = runner.invoke(main, ["show", "Missing"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestRemove:
    def test_remove_with_yes(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        result = invoke(runner, ["remove", "React", "-y"])
        assert "Removed: React" in result.output

    def test_remove_not_found(self, runner):
        result = runner.invoke(main, ["remove", "Missing", "-y"])
        assert result.exit_code != 0

    def test_remove_confirm_abort(self, runner):
        invoke(runner, ["add", "React", "--no-enrich"])
        result = runner.invoke(main, ["remove", "React"], input="n\n")
        assert result.exit_code != 0
        r2 = invoke(runner, ["list"])
        assert "React" in r2.output
