import os
from pathlib import Path
import yaml


def load_config(config_path: str | None = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "sources.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("email", {})
    for key in ("smtp_user", "smtp_pass", "recipient"):
        env_key = key.upper()
        if os.environ.get(env_key):
            config["email"][key] = os.environ[env_key]

    return config
