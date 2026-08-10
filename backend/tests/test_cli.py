"""Tests for the command-line interface.

Thin on purpose, but not absent: a syntax error in cli.py went unnoticed while
the whole suite passed, because nothing imported the module. The entry point is
what a user touches first, so at minimum it has to load and parse arguments.
"""

from __future__ import annotations

import pytest

from lynjax.cli import build_parser, main


class TestParser:
    def test_the_module_imports(self):
        """The regression that prompted this file: cli.py had a syntax error and
        every test still passed, because none of them imported it."""
        assert build_parser() is not None

    @pytest.mark.parametrize(
        "command", ["init", "info", "serve", "audit", "purge", "user"]
    )
    def test_every_documented_command_parses(self, command):
        args = ["user", "a@b.com"] if command == "user" else [command]

        assert build_parser().parse_args(args).command == command

    def test_a_command_is_required(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_an_unknown_command_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["teleport"])

    def test_audit_accepts_its_options(self):
        args = build_parser().parse_args(
            ["audit", "--client", "DGC", "--locale", "en", "--trace", "10.0.0.5"]
        )

        assert args.client == "DGC"
        assert args.locale == "en"
        assert args.trace == "10.0.0.5"

    def test_an_unsupported_locale_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["audit", "--locale", "fr"])

    def test_serve_accepts_host_and_port(self):
        args = build_parser().parse_args(["serve", "--host", "0.0.0.0", "--port", "9000"])

        assert args.host == "0.0.0.0"
        assert args.port == 9000

    def test_user_defaults_to_the_least_privileged_role(self):
        assert build_parser().parse_args(["user", "a@b.com"]).role == "viewer"


class TestSafetyGuards:
    def test_purge_refuses_without_confirmation(self, tmp_path, monkeypatch, capsys):
        """Deleting a client's data must take a deliberate flag."""
        monkeypatch.setenv("LYNJAX_DATA_DIR", str(tmp_path))

        assert main(["purge"]) == 2
        assert "--yes" in capsys.readouterr().err

    def test_audit_refuses_while_the_network_policy_is_closed(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setenv("LYNJAX_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("LYNJAX_NETWORK_POLICY", raising=False)

        from lynjax.core.config import get_settings

        get_settings.cache_clear()
        try:
            assert main(["audit"]) == 2
            assert "authorized-targets" in capsys.readouterr().err
        finally:
            get_settings.cache_clear()
