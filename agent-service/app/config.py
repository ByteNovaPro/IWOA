from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel


class ModelSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-plus"
    backend_base_url: str = "http://localhost:8080"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key.strip())


def load_settings() -> ModelSettings:
    settings_file = Path(__file__).resolve().parent.parent / "config" / "model.local.json"
    file_settings: dict[str, str] = {}
    if settings_file.exists():
        file_settings = json.loads(settings_file.read_text(encoding="utf-8"))

    return ModelSettings(
        api_key=os.getenv("DASHSCOPE_API_KEY", file_settings.get("api_key", "")),
        base_url=os.getenv("DASHSCOPE_BASE_URL", file_settings.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")),
        model=os.getenv("DASHSCOPE_MODEL", file_settings.get("model", "qwen-plus")),
        backend_base_url=os.getenv("BACKEND_BASE_URL", file_settings.get("backend_base_url", "http://localhost:8080")),
    )
