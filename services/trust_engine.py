"""Viraasat.ai — Authenticity Engine

Enterprise-grade trust scoring focused on ONE question:
"Is this product genuinely handcrafted, not factory mass-produced?"

4-Signal Architecture:
  Signal 1: Craft Forensics  (40%) — AI vision analysis of handmade indicators
  Signal 2: Heritage Verify   (25%) — GI tag, regional craft, heritage story
  Signal 3: Identity          (20%) — Warm-start from profile verification
  Signal 4: Community         (15%) — QR scans, shares, product diversity

Design Principles:
  - New artisans get a warm start (~55 from identity alone)
  - No time-decay penalty (artisans may upload seasonally)
  - Gemini scores are converted to deterministic indicators, not raw numbers
  - Scores are transparent and explainable
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, FLASH_MODEL

logger = logging.getLogger(__name__)

# ── Signal Weights ────────────────────────────────────────
WEIGHT_CRAFT_FORENSICS = 0.40
WEIGHT_HERITAGE = 0.25
WEIGHT_IDENTITY = 0.20
WEIGHT_COMMUNITY = 0.15

# ── Gemini Client ─────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ═══════════════════════════════════════════════════════════
# Signal 1: Craft Forensics (40%) — AI-Powered
# ═══════════════════════════════════════════════════════════

FORENSICS_PROMPT = """You are an expert craft authenticator specializing in Indian handicrafts.

Analyze this product image and determine if it is HANDMADE or MASS-PRODUCED.

Look for these HANDMADE indicators (score each 0-100):
1. **thread_irregularity**: Uneven threads, varying thickness, natural fiber texture (hand-spun vs machine-uniform)
2. **tool_marks**: Visible chisel marks on wood, hammer marks on metal, finger impressions on pottery, shuttle marks on textiles
3. **asymmetry**: Slight variations in pattern, non-perfect symmetry (hand-thrown pottery is never perfectly round)
4. **texture_variation**: Uneven glazing, natural dye bleeding, varying weave density
5. **material_authenticity**: Natural fibers/materials vs synthetic/plastic; no factory barcodes or machine-printed labels
6. **unique_pattern**: Each piece differs slightly — not identical to a factory template

Also provide:
- **is_handcrafted**: true/false — your overall assessment
- **confidence**: "high", "medium", or "low"
- **craft_type_detected**: what type of craft this appears to be
- **reasoning**: 1-2 sentence explanation of your assessment

Return ONLY valid JSON:
{
  "thread_irregularity": 0-100,
  "tool_marks": 0-100,
  "asymmetry": 0-100,
  "texture_variation": 0-100,
  "material_authenticity": 0-100,
  "unique_pattern": 0-100,
  "is_handcrafted": true/false,
  "confidence": "high/medium/low",
  "craft_type_detected": "string",
  "reasoning": "string"
}"""


async def _assess_craft_forensics(product_image_bytes: bytes) -> dict:
    """Use Gemini vision to analyze handcraft indicators in the product image."""
    if not _client:
        logger.warning("No Gemini client — returning default forensics score")
        return _default_forensics()

    try:
        response = await asyncio.to_thread(
            _client.models.generate_content,
            model=FLASH_MODEL,
            contents=[
                types.Part.from_bytes(data=product_image_bytes, mime_type="image/jpeg"),
                FORENSICS_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                temperature=0.1,  # Low temp for consistent scoring
            ),
        )

        raw = response.text.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        data = json.loads(raw)

        # Convert 6 indicators to composite score (0-100)
        indicators = [
            data.get("thread_irregularity", 50),
            data.get("tool_marks", 50),
            data.get("asymmetry", 50),
            data.get("texture_variation", 50),
            data.get("material_authenticity", 50),
            data.get("unique_pattern", 50),
        ]
        # Clamp all values to 0-100
        indicators = [max(0, min(100, v)) for v in indicators]
        composite = sum(indicators) / len(indicators)

        return {
            "score": round(composite, 1),
            "is_handcrafted": data.get("is_handcrafted", True),
            "confidence": data.get("confidence", "medium"),
            "craft_type_detected": data.get("craft_type_detected", ""),
            "reasoning": data.get("reasoning", ""),
            "indicators": {
                "thread_irregularity": indicators[0],
                "tool_marks": indicators[1],
                "asymmetry": indicators[2],
                "texture_variation": indicators[3],
                "material_authenticity": indicators[4],
                "unique_pattern": indicators[5],
            },
        }

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Forensics JSON parse failed: {e}")
        return _default_forensics()
    except Exception as e:
        logger.warning(f"Forensics analysis failed: {e}")
        return _default_forensics()


def _default_forensics() -> dict:
    """Neutral default when AI analysis isn't available."""
    return {
        "score": 65.0,
        "is_handcrafted": True,
        "confidence": "low",
        "craft_type_detected": "",
        "reasoning": "AI analysis unavailable — default score assigned",
        "indicators": {
            "thread_irregularity": 65,
            "tool_marks": 65,
            "asymmetry": 65,
            "texture_variation": 65,
            "material_authenticity": 65,
            "unique_pattern": 65,
        },
    }


# ═══════════════════════════════════════════════════════════
# Signal 2: Heritage Verification (25%)
# ═══════════════════════════════════════════════════════════

# Known GI-tagged craft hubs (craft_type → list of known districts/regions)
GI_CRAFT_HUBS = {
    "textiles": [
        "varanasi", "banaras", "kanchipuram", "pochampally", "chanderi",
        "maheshwar", "bhagalpur", "murshidabad", "patan", "sualkuchi",
        "sambalpuri", "ikat", "lucknow", "chikankari", "bagru", "sanganer",
    ],
    "pottery": [
        "khurja", "jaipur", "blue pottery", "kutch", "manipur",
        "longpi", "nizamabad", "black pottery",
    ],
    "jewelry": [
        "jaipur", "rajkot", "nellore", "karimnagar", "thrissur",
        "cuttack", "filigree", "meenakari", "kundan", "thewa",
    ],
    "woodwork": [
        "saharanpur", "mysore", "jodhpur", "kashmir", "bastar",
        "channapatna", "sandalwood", "rosewood",
    ],
    "metalwork": [
        "moradabad", "jagadhri", "thanjavur", "pembarti",
        "bidriware", "bidar", "dhokra", "bastar",
    ],
}


def _verify_heritage(
    parsed_data: dict,
    craft_type: str,
    district: str,
    state: str,
) -> dict:
    """Score heritage authenticity from parsed product data + artisan location."""
    score = 0.0
    reasons = []

    district_lower = (district or "").lower()
    state_lower = (state or "").lower()
    craft_lower = (craft_type or "").lower()

    # 1. GI Tag / Regional Craft Hub Match (0-30 pts)
    known_hubs = GI_CRAFT_HUBS.get(craft_lower, [])
    hub_match = any(
        hub in district_lower or hub in state_lower
        for hub in known_hubs
    )
    if hub_match:
        score += 30
        reasons.append(f"GI craft hub match: {district} is known for {craft_type}")
    elif known_hubs:
        score += 10  # Craft type exists but location doesn't match known hubs
        reasons.append(f"{craft_type} is a recognized craft, location not a known hub")

    # 2. Heritage Story Present + Quality (0-30 pts)
    heritage_story = parsed_data.get("heritage_story", "") or ""
    if len(heritage_story) > 100:
        score += 30
        reasons.append("Rich heritage story present")
    elif len(heritage_story) > 30:
        score += 20
        reasons.append("Heritage story present")
    elif heritage_story:
        score += 10
        reasons.append("Brief heritage mention")

    # 3. Cultural Significance (0-20 pts)
    cultural = parsed_data.get("cultural_significance", "") or ""
    if len(cultural) > 50:
        score += 20
        reasons.append("Cultural significance documented")
    elif cultural:
        score += 10
        reasons.append("Some cultural context")

    # 4. Materials Indicate Traditional Craft (0-20 pts)
    materials = parsed_data.get("materials", [])
    traditional_materials = {
        "silk", "cotton", "wool", "jute", "brass", "copper", "bronze",
        "clay", "terracotta", "wood", "teak", "rosewood", "sandalwood",
        "silver", "gold", "bamboo", "cane", "leather", "lac", "stone",
        "marble", "papier-mache", "khadi", "zari", "linen",
    }
    material_matches = sum(
        1 for m in materials
        if any(tm in m.lower() for tm in traditional_materials)
    )
    if material_matches >= 2:
        score += 20
        reasons.append(f"Traditional materials: {', '.join(materials[:3])}")
    elif material_matches == 1:
        score += 12
        reasons.append(f"Traditional material detected")

    return {
        "score": min(100, score),
        "reasons": reasons,
        "gi_hub_match": hub_match,
    }


# ═══════════════════════════════════════════════════════════
# Signal 3: Identity Verification (20%) — Warm Start
# ═══════════════════════════════════════════════════════════

def _score_identity(profile: dict) -> dict:
    """Score based on profile verification fields. Instant, no AI needed.
    This gives new artisans a warm start on day 1.
    """
    score = 0.0
    verified = []

    # Phone verified (always true if they registered)
    if profile.get("phone"):
        score += 40
        verified.append("phone")

    # Location filled
    if profile.get("district") and profile.get("state"):
        score += 20
        verified.append("location")

    # UPI linked (shows real business intent)
    if profile.get("upi_id"):
        score += 20
        verified.append("upi")

    # Profile photo uploaded
    if profile.get("profile_photo_url"):
        score += 20
        verified.append("photo")

    return {
        "score": min(100, score),
        "verified_fields": verified,
    }


# ═══════════════════════════════════════════════════════════
# Signal 4: Community Engagement (15%)
# ═══════════════════════════════════════════════════════════

async def _score_community(
    artisan_id: str,
    product_count: int,
) -> dict:
    """Score based on community engagement metrics."""
    import database as db

    score = 0.0
    details = {}

    # Product diversity (0-30 pts) — more products = more authentic seller
    if product_count >= 10:
        score += 30
        details["product_diversity"] = "excellent"
    elif product_count >= 5:
        score += 20
        details["product_diversity"] = "good"
    elif product_count >= 2:
        score += 10
        details["product_diversity"] = "growing"
    else:
        details["product_diversity"] = "new"

    # QR scan engagement (0-40 pts)
    try:
        scans = await db.get_scans_for_artisan(artisan_id)
        scan_count = len(scans) if scans else 0
    except Exception:
        scan_count = 0

    if scan_count >= 50:
        score += 40
        details["scan_engagement"] = "viral"
    elif scan_count >= 20:
        score += 30
        details["scan_engagement"] = "high"
    elif scan_count >= 5:
        score += 20
        details["scan_engagement"] = "moderate"
    elif scan_count >= 1:
        score += 10
        details["scan_engagement"] = "starting"
    else:
        details["scan_engagement"] = "none"

    # Repeat activity (0-30 pts) — consistent uploads signal genuine artisan
    if product_count >= 15:
        score += 30
        details["consistency"] = "established"
    elif product_count >= 8:
        score += 20
        details["consistency"] = "regular"
    elif product_count >= 3:
        score += 10
        details["consistency"] = "active"
    else:
        details["consistency"] = "new"

    return {
        "score": min(100, score),
        "details": details,
        "scan_count": scan_count,
    }


# ═══════════════════════════════════════════════════════════
# Master: Compute Authenticity Score
# ═══════════════════════════════════════════════════════════

async def compute_authenticity_score(
    profile: dict,
    parsed_data: dict,
    product_image_bytes: Optional[bytes] = None,
) -> dict:
    """
    Compute the composite authenticity score from all 4 signals.

    Returns a full breakdown:
    {
        "trust_score": 0-100 (composite),
        "is_handcrafted": bool,
        "confidence": "low/medium/high",
        "breakdown": {
            "craft_forensics": { score, indicators, ... },
            "heritage_verification": { score, reasons, ... },
            "identity_verification": { score, verified_fields },
            "community_engagement": { score, details, ... },
        }
    }
    """
    craft_type = ""
    if profile.get("craft_types"):
        craft_type = profile["craft_types"][0] if isinstance(profile["craft_types"], list) else profile["craft_types"]

    # Run signals in parallel (forensics is async/AI, community is async/DB)
    async def _default_forensics_async():
        return _default_forensics()

    forensics_task = (
        _assess_craft_forensics(product_image_bytes)
        if product_image_bytes
        else _default_forensics_async()
    )

    community_task = _score_community(
        artisan_id=profile.get("id", ""),
        product_count=profile.get("product_count", 0),
    )

    # These are sync but fast
    heritage = _verify_heritage(
        parsed_data=parsed_data,
        craft_type=craft_type,
        district=profile.get("district", ""),
        state=profile.get("state", ""),
    )

    identity = _score_identity(profile)

    # Await parallel tasks
    forensics, community = await asyncio.gather(
        forensics_task, community_task, return_exceptions=True
    )

    # Handle exceptions
    if isinstance(forensics, Exception):
        logger.warning(f"Forensics failed: {forensics}")
        forensics = _default_forensics()
    if isinstance(community, Exception):
        logger.warning(f"Community scoring failed: {community}")
        community = {"score": 0, "details": {}, "scan_count": 0}

    # ── Weighted Composite ──
    composite = (
        forensics["score"] * WEIGHT_CRAFT_FORENSICS
        + heritage["score"] * WEIGHT_HERITAGE
        + identity["score"] * WEIGHT_IDENTITY
        + community["score"] * WEIGHT_COMMUNITY
    )

    # Determine overall confidence
    if forensics.get("confidence") == "high" and heritage.get("gi_hub_match"):
        confidence = "high"
    elif forensics.get("confidence") == "low":
        confidence = "low"
    else:
        confidence = "medium"

    return {
        "trust_score": round(composite, 1),
        "is_handcrafted": forensics.get("is_handcrafted", True),
        "confidence": confidence,
        "craft_type_detected": forensics.get("craft_type_detected", ""),
        "breakdown": {
            "craft_forensics": forensics,
            "heritage_verification": heritage,
            "identity_verification": identity,
            "community_engagement": community,
        },
    }
