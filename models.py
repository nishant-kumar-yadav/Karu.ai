"""Viraasat.ai — Pydantic Models"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────

class CraftType(str, Enum):
    TEXTILES = "textiles"
    POTTERY = "pottery"
    JEWELRY = "jewelry"
    WOODWORK = "woodwork"
    METALWORK = "metalwork"
    LEATHER = "leather"
    PAPER = "paper"
    PAINTINGS = "paintings"
    CANE_BAMBOO = "cane_bamboo"
    GENERIC = "generic"


class BadgeLevel(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    MASTER = "master"
    HERITAGE = "heritage"


class SharePlatform(str, Enum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


# ── Auth ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+?\d{10,13}$")


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


class OTPResponse(BaseModel):
    message: str
    phone: str


# ── Artisan Profile ──────────────────────────────────────

class ArtisanCreate(BaseModel):
    phone: str
    name: str
    district: str
    state: str
    craft_types: list[CraftType]
    profile_photo_url: Optional[str] = None
    upi_id: Optional[str] = None
    preferred_language: str = "hi"
    voice_intro_text: Optional[str] = None


class ArtisanProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone: str
    name: str
    district: str
    state: str
    craft_types: list[str]
    profile_photo_url: Optional[str] = None
    upi_id: Optional[str] = None
    heritage_story: Optional[str] = None
    experience_years: Optional[int] = None
    skills: list[str] = []
    trust_score: float = 0.0
    brand_colors: list[str] = []
    monogram_url: Optional[str] = None
    preferred_language: str = "hi"
    badge_level: str = "new"
    product_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ArtisanUpdate(BaseModel):
    name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    craft_types: Optional[list[CraftType]] = None
    upi_id: Optional[str] = None
    preferred_language: Optional[str] = None
    heritage_story: Optional[str] = None
    experience_years: Optional[int] = None
    skills: Optional[list[str]] = None


class ProfileCompletion(BaseModel):
    percentage: int
    missing_fields: list[str]
    nudges: list[str]


# ── Product Generation ───────────────────────────────────

class ProductGenerateRequest(BaseModel):
    artisan_id: str
    voice_description: Optional[str] = None
    product_type: Optional[str] = None
    materials: Optional[list[str]] = None
    price_asked: Optional[float] = None
    preferred_language: str = "hi"


class GeminiParsedOutput(BaseModel):
    """Combined Gemini extraction from voice + image."""
    model_config = {"extra": "ignore"}

    product_type: str = ""
    materials: list[str] = []
    description: str = ""
    heritage_story: str = ""
    cultural_significance: str = ""
    crafting_time: str = ""
    price_min: float = 0
    price_max: float = 0
    price_recommended: float = 0
    price_artisan_asked: float = 0
    seo_keywords: list[str] = []
    features: list[str] = []
    unique_details: str = ""
    color_description: str = ""
    texture_description: str = ""
    background_suggestion: str = "clean white studio"
    # Context-aware scene fields (for smart image generation)
    is_handcrafted: bool = True
    lifestyle_setting: str = ""
    heritage_setting: str = ""
    macro_focus_area: str = ""
    description_amazon: str = ""
    description_instagram: str = ""
    description_whatsapp: str = ""


class GeneratedCard(BaseModel):
    card_type: str
    filename: str
    description: str


class ProductResponse(BaseModel):
    product_id: str
    artisan_id: str
    cards: list[GeneratedCard]
    parsed_data: GeminiParsedOutput
    provenance_hash: str
    trust_score: float
    processing_time_seconds: float


# ── Price Advisor ────────────────────────────────────────

class PriceAdvice(BaseModel):
    min_price: float
    max_price: float
    recommended_price: float
    reasoning: str
    similar_products: list[str] = []


# ── Heritage ─────────────────────────────────────────────

class HeritageInfo(BaseModel):
    origin_story: str
    region: str
    history_years: Optional[int] = None
    gi_tagged: bool = False
    cultural_significance: str
    famous_practitioners: list[str] = []


# ── Sharing ──────────────────────────────────────────────

class ShareData(BaseModel):
    platform: str
    caption: str
    hashtags: list[str] = []
    image_paths: list[str] = []
    deep_link: Optional[str] = None


class LandingPageData(BaseModel):
    html: str
    url: str


class DownloadKit(BaseModel):
    zip_path: str
    file_count: int


# ── A/B Testing ──────────────────────────────────────────

class ABTestResult(BaseModel):
    winner: str
    confidence: float
    reasoning: str
    variant_a_score: float
    variant_b_score: float


# ── Compliance ───────────────────────────────────────────

class ComplianceCheck(BaseModel):
    platform_ready: bool
    checks: dict[str, bool]
    issues: list[str] = []
