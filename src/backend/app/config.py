from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


@dataclass
class Settings:
    razorpay_key_id: str = field(
        default_factory=lambda: os.getenv("RAZORPAY_KEY_ID", "")
    )
    razorpay_key_secret: str = field(
        default_factory=lambda: os.getenv("RAZORPAY_KEY_SECRET", "")
    )
    razorpay_webhook_secret: str = field(
        default_factory=lambda: os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    )
    data_file: str = field(
        default_factory=lambda: os.getenv("GUARD_DATA_FILE", "data/state.json")
    )
    host: str = field(default_factory=lambda: os.getenv("GUARD_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("GUARD_PORT", "8000")))

    @property
    def razorpay_live(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


settings = Settings()
