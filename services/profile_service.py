"""Viraasat.ai — Profile Service

Manages artisan profiles: creation, growing profile, badge levels, trust score.
Zero-form strategy — profile grows automatically with each interaction.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

from PIL import Image

import database as db
from config import BADGE_LEVELS
from models import ArtisanProfile, ArtisanCreate, ArtisanUpdate, ProfileCompletion
from services.ai_pipeline import extract_voice_intro
from services.pillow_engine import create_monogram, extract_brand_colors

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Profile Creation
# ═══════════════════════════════════════════════════════════

async def create_profile(data: ArtisanCreate) -> ArtisanProfile:
    """Create a new artisan profile with auto-generated monogram."""
    artisan_id = str(uuid.uuid4())

    profile_data = {
        "id": artisan_id,
        "phone": data.phone,
        "name": data.name,
        "district": data.district,
        "state": data.state,
        "craft_types": [ct.value for ct in data.craft_types],
        "profile_photo_url": data.profile_photo_url,
        "upi_id": data.upi_id,
        "preferred_language": data.preferred_language,
        "heritage_story": None,
        "experience_years": None,
        "skills": [],
        "trust_score": 0.0,
        "brand_colors": [],
        "monogram_url": None,
        "badge_level": "new",
        "product_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Extract voice intro data if provided
    if data.voice_intro_text:
        try:
            intro_data = await extract_voice_intro(data.voice_intro_text)
            if intro_data.get("experience_years"):
                profile_data["experience_years"] = intro_data["experience_years"]
            if intro_data.get("story_snippet"):
                profile_data["heritage_story"] = intro_data["story_snippet"]
            if intro_data.get("skills_mentioned"):
                profile_data["skills"] = intro_data["skills_mentioned"]
        except Exception as e:
            logger.warning(f"Voice intro extraction failed: {e}")

    await db.create_artisan(profile_data)
    return ArtisanProfile(**profile_data)


# ═══════════════════════════════════════════════════════════
# Get / Update Profile
# ═══════════════════════════════════════════════════════════

async def get_profile(artisan_id: str) -> Optional[ArtisanProfile]:
    """Get artisan profile by ID."""
    data = await db.get_artisan(artisan_id)
    if data:
        return ArtisanProfile(**data)
    return None


async def get_profile_by_phone(phone: str) -> Optional[ArtisanProfile]:
    """Get artisan profile by phone number."""
    data = await db.get_artisan_by_phone(phone)
    if data:
        return ArtisanProfile(**data)
    return None


async def update_profile(artisan_id: str, update: ArtisanUpdate) -> ArtisanProfile:
    """Update artisan profile fields."""
    update_data = update.model_dump(exclude_none=True)
    if "craft_types" in update_data:
        update_data["craft_types"] = [ct.value for ct in update_data["craft_types"]]

    data = await db.update_artisan(artisan_id, update_data)
    return ArtisanProfile(**data)


# ═══════════════════════════════════════════════════════════
# Growing Profile — auto-enrich on every product upload
# ═══════════════════════════════════════════════════════════

async def enrich_profile_from_product(
    artisan_id: str,
    parsed_data: dict,
    product_image: Optional[Image.Image] = None,
) -> ArtisanProfile:
    """
    Auto-enrich the artisan profile after each product upload.
    Adds new skills, materials, updates brand colors, recalculates badge.
    """
    profile = await get_profile(artisan_id)
    if not profile:
        raise ValueError(f"Artisan {artisan_id} not found")

    updates = {}

    # Auto-detect and add new skills from product data
    new_materials = parsed_data.get("materials", [])
    existing_skills = set(profile.skills)
    new_skills = [m for m in new_materials if m not in existing_skills]
    if new_skills:
        updates["skills"] = list(existing_skills | set(new_skills))

    # Append to heritage story if new info
    new_heritage = parsed_data.get("heritage_story", "")
    if new_heritage and new_heritage not in (profile.heritage_story or ""):
        current = profile.heritage_story or ""
        if current:
            updates["heritage_story"] = f"{current} {new_heritage}"
        else:
            updates["heritage_story"] = new_heritage

    # Update brand colors from product image
    if product_image:
        colors = extract_brand_colors(product_image)
        if colors:
            updates["brand_colors"] = colors

    # Increment product count
    updates["product_count"] = profile.product_count + 1

    # Recalculate badge level
    new_count = updates.get("product_count", profile.product_count)
    new_trust = profile.trust_score
    updates["badge_level"] = _calculate_badge(new_count, new_trust)

    if updates:
        data = await db.update_artisan(artisan_id, updates)
        return ArtisanProfile(**data)

    return profile


# ═══════════════════════════════════════════════════════════
# Badge & Trust
# ═══════════════════════════════════════════════════════════

def _calculate_badge(product_count: int, trust_score: float) -> str:
    """Determine the highest badge level an artisan qualifies for."""
    level = "new"
    for badge_id, reqs in BADGE_LEVELS.items():
        if (product_count >= reqs["min_products"] and trust_score >= reqs["min_trust"]):
            level = badge_id
    return level


def calculate_trust_score(product_scores: list[float]) -> float:
    """Average trust score across all products."""
    if not product_scores:
        return 0.0
    return round(sum(product_scores) / len(product_scores), 1)


# ═══════════════════════════════════════════════════════════
# Profile Completion & Gamification
# ═══════════════════════════════════════════════════════════

def get_profile_completion(profile: ArtisanProfile) -> ProfileCompletion:
    """Calculate profile completion percentage and nudges."""
    fields = {
        "name": (profile.name, 15),
        "district": (profile.district, 10),
        "craft_types": (len(profile.craft_types) > 0, 10),
        "heritage_story": (profile.heritage_story, 15),
        "experience_years": (profile.experience_years is not None, 10),
        "upi_id": (profile.upi_id, 10),
        "skills": (len(profile.skills) >= 3, 10),
        "brand_colors": (len(profile.brand_colors) > 0, 5),
        "profile_photo_url": (profile.profile_photo_url, 5),
        "product_count_3": (profile.product_count >= 3, 10),
    }

    total = 0
    missing = []
    for field, (value, weight) in fields.items():
        if value:
            total += weight
        else:
            missing.append(field)

    nudges = []
    nudge_map = {
        "heritage_story": "+15% → Add voice intro about your craft heritage",
        "upi_id": "+10% → Add UPI ID for direct payments",
        "experience_years": "+10% → Tell us your years of experience",
        "skills": "+10% → Upload 3 more products to auto-detect skills",
        "product_count_3": "+10% → Upload 3 products to unlock Active badge",
        "profile_photo_url": "+5% → Add a profile photo",
    }
    for field in missing:
        if field in nudge_map:
            nudges.append(nudge_map[field])

    return ProfileCompletion(
        percentage=min(100, total),
        missing_fields=missing,
        nudges=nudges[:3],
    )


# ═══════════════════════════════════════════════════════════
# Generate Monogram Image
# ═══════════════════════════════════════════════════════════

async def generate_monogram(
    artisan_id: str,
) -> Image.Image:
    """Generate monogram for an artisan."""
    profile = await get_profile(artisan_id)
    if not profile:
        raise ValueError(f"Artisan {artisan_id} not found")

    craft = profile.craft_types[0] if profile.craft_types else ""
    return create_monogram(profile.name, craft)
