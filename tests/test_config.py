"""Configuration: the home directory, the target's settings, and the operator's ideals."""
import pathlib
import sys

import pytest

from factory import config
from tests.conftest import git


@pytest.mark.fr("FR-020")
def test_the_home_directory_comes_from_the_environment_or_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TOMFACTORY_HOME", str(tmp_path / "elsewhere"))
    assert config.home() == tmp_path / "elsewhere"
    assert (tmp_path / "elsewhere").is_dir()  # created on first use
    monkeypatch.delenv("TOMFACTORY_HOME")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.home() == tmp_path / ".tomfactory"


@pytest.mark.fr("FR-009")
def test_target_settings_are_read_from_the_commit_not_the_disk(target):
    commit = git(target, "rev-parse", "HEAD")
    (target / ".factory.toml").write_text('test_command = "true"\n')  # changed, not committed
    settings = config.read_target_config(target, commit)
    assert settings.test_command == "python -m pytest -q -p no:cacheprovider"
    assert settings.no_tests_exit_code == 5
    assert settings.test_paths == ("tests/",)
    assert settings.docs_paths == ("docs/", "CHANGELOG.md")


@pytest.mark.fr("FR-014")
def test_missing_keys_take_the_defaults_including_the_time_limit(target):
    (target / ".factory.toml").write_text('test_command = "make check"\n')
    git(target, "commit", "-q", "-am", "custom command")
    settings = config.read_target_config(target, git(target, "rev-parse", "HEAD"))
    assert settings.test_command == "make check"
    assert settings.step_timeout_seconds == 900
    assert settings.test_paths == ("tests/",)


@pytest.mark.fr("FR-001")
def test_a_target_without_committed_settings_is_a_readable_error(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    git(bare, "init", "-q", "-b", "main")
    git(bare, "config", "user.name", "T")
    git(bare, "config", "user.email", "t@example.invalid")
    (bare / "readme.txt").write_text("hi\n")
    git(bare, "add", "-A")
    git(bare, "commit", "-q", "-m", "base")
    with pytest.raises(config.ConfigError, match=".factory.toml"):
        config.read_target_config(bare, git(bare, "rev-parse", "HEAD"))
    with pytest.raises(config.ConfigError, match="not a git repository"):
        config.head_commit(tmp_path / "nowhere")
    assert config.head_commit(bare) == git(bare, "rev-parse", "HEAD")


@pytest.mark.fr("FR-020")
def test_ideals_are_the_file_in_the_home_directory_or_empty(home):
    assert config.read_ideals() == ""
    assert config.ideals_path() == home / "ideals.md"
    (home / "ideals.md").write_text("Well-defined layers.\n")
    assert config.read_ideals() == "Well-defined layers.\n"


@pytest.mark.fr("FR-023")
def test_edited_ideals_are_what_the_next_read_returns(home):
    (home / "ideals.md").write_text("first\n")
    assert config.read_ideals() == "first\n"
    (home / "ideals.md").write_text("second\n")
    assert config.read_ideals() == "second\n"


@pytest.mark.fr("FR-009")
def test_the_test_command_is_split_into_words_without_a_shell(target):
    settings = config.read_target_config(target, git(target, "rev-parse", "HEAD"))
    assert config.test_argv(settings) == [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    custom = config.TargetConfig(test_command='make check "two words" ; rm -rf x')
    assert config.test_argv(custom) == ["make", "check", "two words", ";", "rm", "-rf", "x"]


@pytest.mark.fr("FR-034")
def test_the_default_target_files_are_valid_and_ignore_caches():
    import tomllib
    parsed = tomllib.loads(config.DEFAULT_FACTORY_TOML)
    assert set(parsed) == {"test_command", "no_tests_exit_code", "test_paths", "docs_paths",
                           "step_timeout_seconds"}
    ignored = config.DEFAULT_GITIGNORE.split()
    assert {"__pycache__/", ".pytest_cache/", "*.pyc", ".venv/"} <= set(ignored)
    assert config.factory_paths()[0] == pathlib.Path(config.__file__).resolve().parent
