"""Viraasat.ai — Configuration"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ── API Keys (5 keys from separate projects for parallel generation) ──
GEMINI_API_KEYS: list[str] = [
    k for k in [
        os.getenv("GEMINI_API_KEY_1", ""),
        os.getenv("GEMINI_API_KEY_2", ""),
        os.getenv("GEMINI_API_KEY_3", ""),
        os.getenv("GEMINI_API_KEY_4", ""),
        os.getenv("GEMINI_API_KEY_5", ""),
    ] if k and not k.startswith("PASTE")
]
# Fallback: legacy single-key env var
if not GEMINI_API_KEYS:
    _legacy = os.getenv("GEMINI_API_KEY", "")
    if _legacy:
        GEMINI_API_KEYS = [_legacy]

GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ── AI Models ─────────────────────────────────────────────
FLASH_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-3.1-flash-image-preview"

# ── Image Settings ────────────────────────────────────────
OUTPUT_SIZE = (2000, 2000)
PADDING_PX = 5

# ── Paths ─────────────────────────────────────────────────
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = BASE_DIR / "static"
FONTS_DIR = STATIC_DIR / "fonts"
TEMPLATES_DIR = BASE_DIR / "templates"

# ── Font (bundled Poppins or fallback) ────────────────────
FONT_BOLD = str(FONTS_DIR / "Poppins-Bold.ttf")
FONT_REGULAR = str(FONTS_DIR / "Poppins-Regular.ttf")
FONT_SEMIBOLD = str(FONTS_DIR / "Poppins-SemiBold.ttf")

# ── Colors (brand palette) ───────────────────────────────
NAVY = (18, 32, 56)
WHITE = (255, 255, 255)
TEAL = (0, 150, 136)
GOLD = (212, 175, 55)
LIGHT_GRAY = (245, 245, 245)

# ── Server ────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ── Language Support ──────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "hi": "hi-IN",
    "en": "en-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
}
DEFAULT_LANGUAGE = "hi"

# ── Badge Levels ──────────────────────────────────────────
BADGE_LEVELS = {
    "new": {"label": "New Artisan", "emoji": "🥉", "min_products": 0, "min_trust": 0},
    "active": {"label": "Active Artisan", "emoji": "🥈", "min_products": 5, "min_trust": 0},
    "master": {"label": "Master Artisan", "emoji": "🥇", "min_products": 15, "min_trust": 75},
    "heritage": {"label": "Heritage Master", "emoji": "💎", "min_products": 25, "min_trust": 85},
}

# ── Category Templates ────────────────────────────────────
CRAFT_CATEGORIES = [
    "textiles", "pottery", "jewelry", "woodwork",
    "metalwork", "leather", "paper", "paintings",
    "cane_bamboo", "generic",
]
