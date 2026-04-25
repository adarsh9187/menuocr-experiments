from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal


PACKAGE_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = PACKAGE_DIR.parent
REPO_ROOT = EXPERIMENTS_DIR.parent

ENV_PATH = EXPERIMENTS_DIR / ".env"
TARGET_SCHEMA_PATH = REPO_ROOT / "menuocr" / "schemas" / "category_item_minimal.schema.json"
PROMPT_PATH = PACKAGE_DIR / "prompt.md"

ModelName = Literal["gpt-4o", "text-embedding-ada-002"]

MODEL_CONFIG: Dict[str, Dict[str, str]] = {
    "gpt-4o": {
        "endpoint_env": "AZURE_OPENAI_GPT4O_ENDPOINT",
        "key_env": "AZURE_OPENAI_GPT4O_API_KEY",
        "kind": "chat",
    },
    "text-embedding-ada-002": {
        "endpoint_env": "AZURE_OPENAI_EMBEDDING_ENDPOINT",
        "key_env": "AZURE_OPENAI_EMBEDDING_API_KEY",
        "kind": "embedding",
    },
}
