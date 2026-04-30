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

    def conn_fn():
        return get_connection(db_path)

    with (
        patch("nexus.cli.get_connection", conn_fn),
        patch("nexus.cli_project.get_connection", conn_fn),
    ):
        yield CliRunner()


def invoke(runner: CliRunner, args: list[str]):
    return runner.invoke(main, args, catch_exceptions=False)


class TestProjectAdd:
    def test_add_basic(self, runner):
        result = invoke(runner, ["project", "add", "myapp"])
        assert result.exit_code == 0
        assert "Added project: myapp" in result.output

    def test_add_with_path(self, runner, tmp_path):
        d = tmp_path / "proj"
        d.mkdir()
        result = invoke(runner, ["project", "add", "myapp", "-p", str(d)])
        assert result.exit_code == 0
        assert "Added project: myapp" in result.output

    def test_add_duplicate(self, runner):
        invoke(runner, ["project", "add", "myapp"])
        result = runner.invoke(main, ["project", "add", "myapp"])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_add_nonexistent_path(self, runner, tmp_path):
        bad = tmp_path / "nope"
        result = runner.invoke(main, ["project", "add", "myapp", "-p", str(bad)])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_add_duplicate_path(self, runner, tmp_path):
        d = tmp_path / "proj"
        d.mkdir()
        invoke(runner, ["project", "add", "first", "-p", str(d)])
        result = runner.invoke(main, ["project", "add", "second", "-p", str(d)])
        assert result.exit_code != 0
        assert "already registered" in result.output


class TestProjectList:
    def test_list_empty(self, runner):
        result = invoke(runner, ["project", "list"])
        assert "No projects yet" in result.output

    def test_list_with_projects(self, runner):
        invoke(runner, ["project", "add", "alpha"])
        invoke(runner, ["project", "add", "beta"])
        result = invoke(runner, ["project", "list"])
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_list_json(self, runner):
        invoke(runner, ["project", "add", "alpha"])
        result = invoke(runner, ["project", "list", "--format", "json"])
        assert '"name": "alpha"' in result.output


class TestProjectShow:
    def test_show_basic(self, runner):
        invoke(runner, ["project", "add", "myapp", "-d", "A test project"])
        result = invoke(runner, ["project", "show", "myapp"])
        assert "Project: myapp" in result.output
        assert "A test project" in result.output
        assert "Concepts: 0" in result.output

    def test_show_not_found(self, runner):
        result = runner.invoke(main, ["project", "show", "missing"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestProjectRemove:
    def test_remove_with_yes(self, runner):
        invoke(runner, ["project", "add", "myapp"])
        result = invoke(runner, ["project", "remove", "myapp", "-y"])
        assert result.exit_code == 0
        assert "Removed project: myapp" in result.output

    def test_remove_not_found(self, runner):
        result = runner.invoke(main, ["project", "remove", "missing", "-y"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_remove_confirm_abort(self, runner):
        invoke(runner, ["project", "add", "myapp"])
        result = runner.invoke(main, ["project", "remove", "myapp"], input="n\n")
        assert result.exit_code != 0
        # Project should still exist
        r2 = invoke(runner, ["project", "list"])
        assert "myapp" in r2.output
