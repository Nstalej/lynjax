"""Tests for the configuration layer.

These exist because the NetVault config this replaces looked correct and was
silently broken: nested models meant environment variables were never read, and
the defaults happened to match what the developer wanted, so nothing failed
visibly. Every test below pins behaviour that used to be assumed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from lynjax.core.config import (
    ConfigError,
    Settings,
    ensure_runtime_secrets,
    get_settings,
    load_env_file,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Drop any LYNJAX_* variable so the developer's shell cannot skew results."""
    for key in [k for k in os.environ if k.startswith("LYNJAX_")]:
        monkeypatch.delenv(key, raising=False)


class TestEnvironmentVariablesAreActuallyRead:
    """The exact failure mode that made NetVault's config dead weight."""

    def test_port_comes_from_environment(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_PORT", "9000")

        assert Settings().port == 9000

    def test_log_level_comes_from_environment(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_LOG_LEVEL", "DEBUG")

        assert Settings().log_level == "DEBUG"

    def test_data_dir_comes_from_environment(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LYNJAX_DATA_DIR", str(tmp_path))

        assert Settings().data_dir == tmp_path

    def test_environment_name_comes_from_environment(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_ENVIRONMENT", "production")

        assert Settings().environment == "production"


class TestValidation:
    def test_out_of_range_port_is_rejected(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_PORT", "70000")

        with pytest.raises(ValidationError):
            Settings()

    def test_unknown_log_level_is_rejected(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_LOG_LEVEL", "CHATTY")

        with pytest.raises(ValidationError):
            Settings()

    def test_unknown_network_policy_is_rejected(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_NETWORK_POLICY", "scan-everything")

        with pytest.raises(ValidationError):
            Settings()


class TestDerivedPaths:
    def test_db_path_sits_inside_the_data_dir(self, tmp_path):
        settings = Settings(data_dir=tmp_path)

        assert settings.db_path == tmp_path / "lynjax.db"

    def test_secrets_file_sits_inside_the_data_dir(self, tmp_path):
        settings = Settings(data_dir=tmp_path)

        assert settings.secrets_file == tmp_path / "secrets.env"

    def test_user_supplied_path_expands_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("LYNJAX_DATA_DIR", "~/lynjax-data")

        assert Settings().data_dir == tmp_path / "lynjax-data"


class TestSafetyDefault:
    def test_real_network_access_is_off_by_default(self):
        """A tool that can reach infrastructure must not do so unasked."""
        settings = Settings()

        assert settings.network_policy == "simulated-checks-only"
        assert settings.simulated_only is True

    def test_authorized_mode_must_be_opted_into(self, monkeypatch):
        monkeypatch.setenv("LYNJAX_NETWORK_POLICY", "authorized-targets")

        assert Settings().simulated_only is False


class TestSecretBootstrap:
    def test_missing_secrets_are_generated_and_persisted(self, tmp_path):
        settings = ensure_runtime_secrets(Settings(data_dir=tmp_path))

        assert settings.secret_key
        assert settings.credentials_master_key
        assert settings.secrets_file.exists()

    def test_generated_secrets_survive_a_restart(self, tmp_path):
        """Regenerating the master key would orphan every stored credential."""
        first = ensure_runtime_secrets(Settings(data_dir=tmp_path))
        second = ensure_runtime_secrets(Settings(data_dir=tmp_path))

        assert first.secret_key == second.secret_key
        assert first.credentials_master_key == second.credentials_master_key

    def test_generated_master_key_is_a_usable_fernet_key(self, tmp_path):
        from cryptography.fernet import Fernet

        settings = ensure_runtime_secrets(Settings(data_dir=tmp_path))
        fernet = Fernet(settings.credentials_master_key.encode("utf-8"))

        assert fernet.decrypt(fernet.encrypt(b"probe")) == b"probe"

    def test_environment_supplied_secret_wins_and_is_not_written_to_disk(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("LYNJAX_SECRET_KEY", "operator-provided-secret")

        settings = ensure_runtime_secrets(Settings(data_dir=tmp_path))

        assert settings.secret_key == "operator-provided-secret"
        assert "operator-provided-secret" not in settings.secrets_file.read_text()

    def test_two_installs_do_not_share_a_master_key(self, tmp_path):
        one = ensure_runtime_secrets(Settings(data_dir=tmp_path / "a"))
        two = ensure_runtime_secrets(Settings(data_dir=tmp_path / "b"))

        assert one.credentials_master_key != two.credentials_master_key

    def test_data_dir_is_created_when_absent(self, tmp_path):
        target = tmp_path / "does" / "not" / "exist"

        ensure_runtime_secrets(Settings(data_dir=target))

        assert target.is_dir()


class TestFailureReporting:
    def test_unwritable_data_dir_raises_instead_of_killing_the_process(self, tmp_path):
        """NetVault called sys.exit(1) here, which is fatal for an installed CLI."""
        blocker = tmp_path / "blocked"
        blocker.write_text("I am a file, not a directory")

        with pytest.raises(ConfigError) as excinfo:
            ensure_runtime_secrets(Settings(data_dir=blocker / "data"))

        assert "LYNJAX_DATA_DIR" in str(excinfo.value)


class TestSettingsCache:
    def test_get_settings_returns_a_cached_instance(self):
        assert get_settings() is get_settings()


class TestStrayEnvFilesAreIgnored:
    """A .env in the working directory must not configure an installed tool.

    Found by installing the wheel and running it from another folder: the app
    reported a different name because it had read that folder's .env. The same
    path let an unprefixed NETWORK_POLICY flip real network access on, which is
    the guard the whole product leans on.
    """

    @pytest.fixture
    def hostile_cwd(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text(
            "APP_NAME=Compromised\n"
            "SECRET_KEY=injected-by-a-stray-file\n"
            "NETWORK_POLICY=authorized-targets\n"
            "DATA_DIR=/somewhere/else\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        return tmp_path

    def test_a_stray_env_file_cannot_rename_the_app(self, hostile_cwd):
        assert Settings().app_name == "Lynjax"

    def test_a_stray_env_file_cannot_set_the_signing_key(self, hostile_cwd):
        assert Settings().secret_key is None

    def test_a_stray_env_file_cannot_enable_real_network_access(self, hostile_cwd):
        """The one that matters: the guard must not be switchable by a file
        that merely happens to sit in the current directory."""
        assert Settings().network_policy == "simulated-checks-only"

    def test_a_stray_env_file_cannot_redirect_the_data_directory(self, hostile_cwd):
        assert Settings().data_dir != Path("/somewhere/else")


class TestExplicitEnvFile:
    def test_a_named_file_is_loaded(self, tmp_path, monkeypatch):
        target = tmp_path / "lynjax.env"
        target.write_text("LYNJAX_PORT=9123\n", encoding="utf-8")
        monkeypatch.setenv("LYNJAX_ENV_FILE", str(target))

        load_env_file()

        assert Settings().port == 9123

    def test_unprefixed_keys_are_ignored(self, tmp_path, monkeypatch):
        """Ignored rather than guessed at: that confusion is what leaked."""
        target = tmp_path / "lynjax.env"
        target.write_text(
            "PORT=9123\nNETWORK_POLICY=authorized-targets\n", encoding="utf-8"
        )
        monkeypatch.setenv("LYNJAX_ENV_FILE", str(target))

        load_env_file()

        assert Settings().port == 8080
        assert Settings().network_policy == "simulated-checks-only"

    def test_an_existing_variable_wins_over_the_file(self, tmp_path, monkeypatch):
        target = tmp_path / "lynjax.env"
        target.write_text("LYNJAX_PORT=9123\n", encoding="utf-8")
        monkeypatch.setenv("LYNJAX_ENV_FILE", str(target))
        monkeypatch.setenv("LYNJAX_PORT", "7000")

        load_env_file()

        assert Settings().port == 7000

    def test_a_missing_file_is_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LYNJAX_ENV_FILE", str(tmp_path / "absent.env"))

        assert load_env_file() == {}

    def test_nothing_is_read_when_no_file_is_named(self):
        assert load_env_file() == {}
