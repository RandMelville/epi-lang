"""
Tests for `epi init <name>` — project bootstrap command.

Verifies that templates packaged inside the wheel are correctly materialised
into a fresh project directory, and that the command refuses to clobber an
existing directory without --force.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from epi.cli import app


runner = CliRunner()


@pytest.fixture
def in_tmp_path(tmp_path, monkeypatch):
    """Run each test with cwd set to a fresh tmp directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestEpiInit:
    def test_init_creates_directory(self, in_tmp_path):
        result = runner.invoke(app, ["init", "my-test-proj"])
        assert result.exit_code == 0, result.output
        project = in_tmp_path / "my-test-proj"
        assert project.is_dir()

    def test_init_writes_contrato_epi(self, in_tmp_path):
        result = runner.invoke(app, ["init", "my-test-proj"])
        assert result.exit_code == 0, result.output
        contrato = in_tmp_path / "my-test-proj" / "contrato.epi"
        assert contrato.is_file()
        body = contrato.read_text()
        assert "@Language: Epi v0.3" in body
        assert "Entity Contrato" in body

    def test_init_writes_prompts(self, in_tmp_path):
        result = runner.invoke(app, ["init", "my-test-proj"])
        assert result.exit_code == 0, result.output
        prompt = in_tmp_path / "my-test-proj" / "prompts" / "legal_scan_simples.md"
        assert prompt.is_file()
        body = prompt.read_text()
        assert "_confidence" in body
        assert "risco" in body

    def test_init_writes_readme(self, in_tmp_path):
        result = runner.invoke(app, ["init", "my-test-proj"])
        assert result.exit_code == 0, result.output
        readme = in_tmp_path / "my-test-proj" / "README.md"
        assert readme.is_file()
        assert "epi transpile" in readme.read_text()

    def test_init_twice_without_force_fails(self, in_tmp_path):
        first = runner.invoke(app, ["init", "dup-proj"])
        assert first.exit_code == 0, first.output

        second = runner.invoke(app, ["init", "dup-proj"])
        assert second.exit_code != 0
        assert "already exists" in second.output
        assert "--force" in second.output

    def test_init_with_force_overwrites(self, in_tmp_path):
        first = runner.invoke(app, ["init", "force-proj"])
        assert first.exit_code == 0, first.output

        # Add a sentinel file that should disappear after --force.
        sentinel = in_tmp_path / "force-proj" / "sentinel.txt"
        sentinel.write_text("delete me")
        assert sentinel.exists()

        second = runner.invoke(app, ["init", "force-proj", "--force"])
        assert second.exit_code == 0, second.output
        assert not sentinel.exists()
        # Fresh contrato.epi should still be there.
        assert (in_tmp_path / "force-proj" / "contrato.epi").is_file()
