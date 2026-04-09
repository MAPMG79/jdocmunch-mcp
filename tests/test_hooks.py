"""Tests for CLI hook handlers and init --hooks installer."""

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# PreToolUse hook
# ---------------------------------------------------------------------------

class TestPreToolUse:
    """Tests for hook-pretooluse handler."""

    def _run(self, payload: dict) -> int:
        from jdocmunch_mcp.cli.hooks import run_pretooluse
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            return run_pretooluse()

    def test_allows_non_doc_file(self):
        assert self._run({"tool_input": {"file_path": "app.py"}}) == 0

    def test_allows_small_doc_file(self, tmp_path):
        p = tmp_path / "small.md"
        p.write_text("hi")
        assert self._run({"tool_input": {"file_path": str(p)}}) == 0

    def test_warns_on_large_doc_file(self, tmp_path, capsys):
        p = tmp_path / "big.md"
        p.write_text("x" * 5000)
        assert self._run({"tool_input": {"file_path": str(p)}}) == 0
        captured = capsys.readouterr()
        assert "jDocMunch hint" in captured.err

    def test_allows_targeted_read(self, tmp_path):
        p = tmp_path / "big.md"
        p.write_text("x" * 5000)
        assert self._run({"tool_input": {"file_path": str(p), "offset": 10, "limit": 5}}) == 0

    def test_allows_rst_small(self, tmp_path):
        p = tmp_path / "doc.rst"
        p.write_text("hi")
        assert self._run({"tool_input": {"file_path": str(p)}}) == 0

    def test_warns_on_large_rst(self, tmp_path, capsys):
        p = tmp_path / "doc.rst"
        p.write_text("x" * 5000)
        assert self._run({"tool_input": {"file_path": str(p)}}) == 0
        assert "jDocMunch hint" in capsys.readouterr().err

    def test_warns_on_large_adoc(self, tmp_path, capsys):
        p = tmp_path / "doc.adoc"
        p.write_text("x" * 5000)
        assert self._run({"tool_input": {"file_path": str(p)}}) == 0
        assert "jDocMunch hint" in capsys.readouterr().err

    def test_handles_invalid_json(self):
        from jdocmunch_mcp.cli.hooks import run_pretooluse
        with mock.patch("sys.stdin", io.StringIO("not json")):
            assert run_pretooluse() == 0

    def test_handles_missing_file_path(self):
        assert self._run({"tool_input": {}}) == 0

    def test_handles_nonexistent_file(self):
        assert self._run({"tool_input": {"file_path": "/nonexistent/doc.md"}}) == 0


# ---------------------------------------------------------------------------
# PostToolUse hook
# ---------------------------------------------------------------------------

class TestPostToolUse:
    """Tests for hook-posttooluse handler."""

    def _run(self, payload: dict) -> int:
        from jdocmunch_mcp.cli.hooks import run_posttooluse
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            return run_posttooluse()

    def test_skips_non_doc_file(self):
        with mock.patch("subprocess.Popen") as mock_popen:
            assert self._run({"tool_input": {"file_path": "app.py"}}) == 0
            mock_popen.assert_not_called()

    def test_spawns_reindex_for_md(self, tmp_path):
        p = tmp_path / "README.md"
        p.write_text("hello")
        with mock.patch("subprocess.Popen") as mock_popen:
            assert self._run({"tool_input": {"file_path": str(p)}}) == 0
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "jdocmunch-mcp"
            assert cmd[1] == "index-local"
            assert "--path" in cmd

    def test_spawns_reindex_for_rst(self, tmp_path):
        p = tmp_path / "doc.rst"
        p.write_text("hello")
        with mock.patch("subprocess.Popen") as mock_popen:
            assert self._run({"tool_input": {"file_path": str(p)}}) == 0
            mock_popen.assert_called_once()

    def test_spawns_reindex_for_txt(self, tmp_path):
        p = tmp_path / "notes.txt"
        p.write_text("hello")
        with mock.patch("subprocess.Popen") as mock_popen:
            assert self._run({"tool_input": {"file_path": str(p)}}) == 0
            mock_popen.assert_called_once()

    def test_handles_invalid_json(self):
        from jdocmunch_mcp.cli.hooks import run_posttooluse
        with mock.patch("sys.stdin", io.StringIO("bad")):
            assert run_posttooluse() == 0

    def test_handles_popen_failure(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("hello")
        with mock.patch("subprocess.Popen", side_effect=FileNotFoundError):
            assert self._run({"tool_input": {"file_path": str(p)}}) == 0


# ---------------------------------------------------------------------------
# PreCompact hook
# ---------------------------------------------------------------------------

class TestPreCompact:
    """Tests for hook-precompact handler."""

    def test_returns_snapshot(self, capsys):
        from jdocmunch_mcp.cli.hooks import run_precompact
        mock_repos = {
            "repos": [{"name": "test-repo", "section_count": 42, "doc_count": 5, "source_root": "/tmp/docs"}],
            "count": 1,
        }
        with mock.patch("sys.stdin", io.StringIO("{}")):
            with mock.patch("jdocmunch_mcp.tools.list_repos.list_repos", return_value=mock_repos):
                assert run_precompact() == 0

        out = capsys.readouterr().out
        result = json.loads(out)
        assert "systemMessage" in result
        assert "test-repo" in result["systemMessage"]

    def test_returns_nothing_when_no_repos(self, capsys):
        from jdocmunch_mcp.cli.hooks import run_precompact
        with mock.patch("sys.stdin", io.StringIO("{}")):
            with mock.patch("jdocmunch_mcp.tools.list_repos.list_repos", return_value={"repos": [], "count": 0}):
                assert run_precompact() == 0
        assert capsys.readouterr().out == ""

    def test_handles_invalid_json(self):
        from jdocmunch_mcp.cli.hooks import run_precompact
        with mock.patch("sys.stdin", io.StringIO("bad")):
            assert run_precompact() == 0


# ---------------------------------------------------------------------------
# init --hooks installer
# ---------------------------------------------------------------------------

class TestInstallHooks:
    """Tests for init --hooks."""

    def test_installs_all_three_hooks(self, tmp_path):
        from jdocmunch_mcp.cli.init import install_hooks, _settings_json_path
        settings = tmp_path / "settings.json"
        settings.write_text("{}")

        with mock.patch("jdocmunch_mcp.cli.init._settings_json_path", return_value=settings):
            msg = install_hooks(backup=False)

        assert "PreToolUse" in msg or "added" in msg
        data = json.loads(settings.read_text())
        hooks = data["hooks"]
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert "PreCompact" in hooks

        # Verify commands
        pre_cmd = hooks["PreToolUse"][0]["hooks"][0]["command"]
        assert pre_cmd == "jdocmunch-mcp hook-pretooluse"
        post_cmd = hooks["PostToolUse"][0]["hooks"][0]["command"]
        assert post_cmd == "jdocmunch-mcp hook-posttooluse"
        compact_cmd = hooks["PreCompact"][0]["hooks"][0]["command"]
        assert compact_cmd == "jdocmunch-mcp hook-precompact"

    def test_idempotent(self, tmp_path):
        from jdocmunch_mcp.cli.init import install_hooks
        settings = tmp_path / "settings.json"
        settings.write_text("{}")

        with mock.patch("jdocmunch_mcp.cli.init._settings_json_path", return_value=settings):
            install_hooks(backup=False)
            msg = install_hooks(backup=False)

        assert "already present" in msg

    def test_preserves_existing_hooks(self, tmp_path):
        from jdocmunch_mcp.cli.init import install_hooks
        settings = tmp_path / "settings.json"
        existing = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Read",
                    "hooks": [{"type": "command", "command": "jcodemunch-mcp hook-pretooluse"}],
                }]
            }
        }
        settings.write_text(json.dumps(existing))

        with mock.patch("jdocmunch_mcp.cli.init._settings_json_path", return_value=settings):
            install_hooks(backup=False)

        data = json.loads(settings.read_text())
        # Both jcodemunch and jdocmunch hooks should be present
        pre_rules = data["hooks"]["PreToolUse"]
        cmds = [r["hooks"][0]["command"] for r in pre_rules]
        assert "jcodemunch-mcp hook-pretooluse" in cmds
        assert "jdocmunch-mcp hook-pretooluse" in cmds

    def test_dry_run(self, tmp_path):
        from jdocmunch_mcp.cli.init import install_hooks
        settings = tmp_path / "settings.json"
        settings.write_text("{}")

        with mock.patch("jdocmunch_mcp.cli.init._settings_json_path", return_value=settings):
            msg = install_hooks(dry_run=True)

        assert "would add" in msg
        # File should still be empty
        assert json.loads(settings.read_text()) == {}

    def test_creates_backup(self, tmp_path):
        from jdocmunch_mcp.cli.init import install_hooks
        settings = tmp_path / "settings.json"
        settings.write_text('{"existing": true}')

        with mock.patch("jdocmunch_mcp.cli.init._settings_json_path", return_value=settings):
            install_hooks(backup=True)

        bak = tmp_path / "settings.json.bak"
        assert bak.exists()
        assert json.loads(bak.read_text()) == {"existing": True}


# ---------------------------------------------------------------------------
# CLI dispatch (server.py main)
# ---------------------------------------------------------------------------

class TestCLIDispatch:
    """Test that CLI subcommands are routed correctly."""

    def test_hook_pretooluse_dispatch(self):
        from jdocmunch_mcp.server import main
        with mock.patch("jdocmunch_mcp.cli.hooks.run_pretooluse", return_value=0) as m:
            with pytest.raises(SystemExit) as exc_info:
                main(["hook-pretooluse"])
            assert exc_info.value.code == 0
            m.assert_called_once()

    def test_hook_posttooluse_dispatch(self):
        from jdocmunch_mcp.server import main
        with mock.patch("jdocmunch_mcp.cli.hooks.run_posttooluse", return_value=0) as m:
            with pytest.raises(SystemExit) as exc_info:
                main(["hook-posttooluse"])
            assert exc_info.value.code == 0
            m.assert_called_once()

    def test_hook_precompact_dispatch(self):
        from jdocmunch_mcp.server import main
        with mock.patch("jdocmunch_mcp.cli.hooks.run_precompact", return_value=0) as m:
            with pytest.raises(SystemExit) as exc_info:
                main(["hook-precompact"])
            assert exc_info.value.code == 0
            m.assert_called_once()

    def test_index_local_dispatch(self, tmp_path):
        from jdocmunch_mcp.server import main
        mock_result = {"status": "ok", "files_indexed": 0}
        with mock.patch("jdocmunch_mcp.tools.index_local.index_local", return_value=mock_result) as m:
            main(["index-local", "--path", str(tmp_path)])
            m.assert_called_once_with(path=str(tmp_path), name=None)

    def test_init_hooks_dispatch(self):
        from jdocmunch_mcp.server import main
        with mock.patch("jdocmunch_mcp.cli.init.run_init") as m:
            main(["init", "--hooks"])
            m.assert_called_once_with(hooks=True, dry_run=False)
