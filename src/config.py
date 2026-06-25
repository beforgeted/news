import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent


def load_config(config_path: str | None = None) -> dict:
    # Load .env from project root (if exists) — gives priority to file, falls back to env vars
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "sources.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("email", {})
    for key in ("smtp_user", "smtp_pass", "recipient"):
        env_key = key.upper()
        if os.environ.get(env_key):
            config["email"][key] = os.environ[env_key]

    if os.environ.get("RECIPIENTS"):
        config["email"]["recipients"] = os.environ["RECIPIENTS"]

    return config
