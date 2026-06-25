import os
import tempfile
from pathlib import Path
from src.config import load_config


def test_load_config_defaults():
    config = load_config()
    assert "github" in config
    assert config["github"]["trending_limit"] == 5
    assert config["github"]["active_limit"] == 5
    assert config["blogs"]["lookback_days"] == 3
    assert len(config["blogs"]["sources"]) == 5
    assert config["blogs"]["max_articles"] == 10
    assert config["arxiv"]["categories"] == ["cs.AI", "cs.CL"]


def test_load_config_env_override(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "secret123")
    monkeypatch.setenv("RECIPIENT", "to@gmail.com")

    config = load_config()
    assert config["email"]["smtp_user"] == "test@gmail.com"
    assert config["email"]["smtp_pass"] == "secret123"
    assert config["email"]["recipient"] == "to@gmail.com"


def test_load_config_custom_path():
    import yaml
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"github": {"topics": ["test-topic"]}}, f)
        tmp_path = f.name

    try:
        config = load_config(tmp_path)
        assert config["github"]["topics"] == ["test-topic"]
    finally:
        os.unlink(tmp_path)
