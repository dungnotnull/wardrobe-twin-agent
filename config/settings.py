"""Application configuration via pydantic-settings."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Central configuration. Reads from env vars or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = DATA_DIR / "models"
    AVATARS_DIR: Path = DATA_DIR / "avatars"
    WARDROBE_IMG_DIR: Path = DATA_DIR / "wardrobe_images"
    CACHE_DIR: Path = DATA_DIR / "cache"
    DB_PATH: Path = DATA_DIR / "wardrobe.db"

    HOST: str = "127.0.0.1"
    PORT: int = 7331
    WS_PORT: int = 7332

    ENCRYPTION_KEY_SALT: bytes = b"wardrobe-twin-agent-salt-v1"

    DEVICE: Literal["cuda", "cpu", "auto"] = "auto"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"

    DENSEPOSE_MODEL_ID: str = "facebook/densepose_rcnn_R_101_FPN_s1x"
    OOTDIFFUSION_MODEL_ID: str = "levihsu/OOTDiffusion"
    FASHIONCLIP_MODEL_ID: str = "patrickjohncyh/fashion-clip"
    BLIP2_MODEL_ID: str = "Salesforce/blip2-opt-2.7b"
    DONUT_MODEL_ID: str = "naver-clova-ix/donut-base"
    CONTROLNET_MODEL_ID: str = "lllyasviel/ControlNet-v1-1"
    SAM_MODEL_ID: str = "facebook/sam-vit-huge"

    CLAUDE_MODEL: str = "claude-opus-4-8"
    GPT4V_MODEL: str = "gpt-4o"
    OLLAMA_MODEL: str = "phi3:mini"

    OOTDIFFUSION_STEPS: int = 20
    OOTDIFFUSION_GUIDANCE_SCALE: float = 7.5

    EMBEDDING_DIM: int = 512
    BLIP2_CONFIDENCE_THRESHOLD: float = 0.7

    PBKDF2_ITERATIONS: int = 480_000

    CRAWL_SCHEDULE_HOUR: int = 2
    CRAWL_SCHEDULE_DAY: str = "mon"

    RESULT_CACHE_MAX_AGE_HOURS: int = 24

    @property
    def effective_device(self) -> str:
        if self.DEVICE != "auto":
            return self.DEVICE
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def ensure_dirs(self) -> None:
        for d in [
            self.DATA_DIR, self.MODELS_DIR, self.AVATARS_DIR,
            self.WARDROBE_IMG_DIR, self.CACHE_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)


settings = AppConfig()
