from pydantic_settings import BaseSettings
from typing import List, Dict
import yaml
import os

class Settings(BaseSettings):
    # SSO / JWT
    JWT_ISSUER: str
    JWT_AUDIENCE: str
    JWKS_URL: str | None = None  # For dynamic key fetching
    JWT_PUBLIC_KEY: str | None = None

    # Security
    ALLOWED_ORIGINS: List[str] = ["*"]

    # vLLM Backends
    MODEL_MAPPING: Dict[str, str] = {}

    # Database
    DB_PATH: str = "/app/data/usage.db"

    class Config:
        env_prefix = "PROXY_"
        env_file = ".env"

settings = Settings()

# Load model mapping from YAML if exists
def load_model_mapping():
    config_path = "/app/config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            if config and "models" in config:
                settings.MODEL_MAPPING = config["models"]

load_model_mapping()
