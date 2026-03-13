"""Viraasat.ai — Heritage Enrichment Service

Uses Gemini with search grounding to pull real historical data
about craft traditions, GI tags, and cultural significance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from google import genai
from google.genai import types

from config import FLASH_MODEL, GEMINI_API_KEY

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

HERITAGE_PROMPT = """You are an expert on Indian craft heritage and GI (Geographical Indication) tags.

Craft type: {craft_type}
Region: {district}, {state}
Product: {product_type}
Artisan's own story: "{artisan_story}"

Research the REAL heritage of this craft tradition. Provide factual, specific information.

Return JSON:
{{
  "origin_story": "2-3 sentences about the craft's origin and history in this region. Include real dates, dynasties, or historical references if available.",
  "region": "The specific region/district known for this craft",
  "history_years": 0,
  "gi_tagged": false,
  "gi_tag_year": null,
  "cultural_significance": "Why this craft is culturally important — its role in festivals, daily life, or economy",
  "famous_practitioners": ["list of famous artisans or families known for this craft"],
  "craft_techniques": ["list of specific traditional techniques used"],
  "raw_materials_source": "Where the raw materials traditionally come from",
  "current_challenges": "Current challenges facing this craft tradition",
  "artisan_count_estimate": "Estimated number of active artisans in this craft"
}}

Be factual and specific. Use real data where possible. If unsure about a field, provide your best estimate and note it."""


async def get_heritage_info(
    craft_type: str,
    district: str = "",
    state: str = "",
    product_type: str = "",
    artisan_story: str = "",
) -> dict:
    """Get heritage enrichment data for a craft tradition."""
    prompt = HERITAGE_PROMPT.format(
        craft_type=craft_type,
        district=district or "unknown district",
        state=state or "India",
        product_type=product_type or craft_type,
        artisan_story=artisan_story or "No personal story shared yet",
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Heritage JSON parse failed: {e}. Raw: {raw[:200]}")
        return {}


# ═══════════════════════════════════════════════════════════
# Heritage Map Content (for landing page)
# ═══════════════════════════════════════════════════════════

async def get_heritage_map_content(
    craft_type: str,
    state: str,
) -> dict:
    """Generate heritage map data for the artisan's region."""
    prompt = f"""For the craft "{craft_type}" in {state}, India, provide:

Return JSON:
{{
  "map_title": "Title for the heritage section",
  "region_description": "1-2 sentences about the region's craft heritage",
  "notable_crafts": ["list of 3-5 notable crafts from this region"],
  "nearby_artisan_communities": ["list of 2-3 nearby craft communities"],
  "craft_trail_suggestion": "A suggested craft trail/visit itinerary for tourists"
}}"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Heritage map JSON parse failed: {e}. Raw: {raw[:200]}")
        return {}
