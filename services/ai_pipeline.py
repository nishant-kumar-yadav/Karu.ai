"""Viraasat.ai — Core AI Pipeline Service

Orchestrates: Voice/text → Gemini parse → enrichment → prompt filling
Uses ONE combined Gemini 2.5 Flash call for maximum efficiency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from io import BytesIO

from google import genai
from google.genai import types

from config import FLASH_MODEL, GEMINI_API_KEY
from models import GeminiParsedOutput

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)


# ═══════════════════════════════════════════════════════════
# Combined Gemini Call — parse + enrich + price + SEO
# ═══════════════════════════════════════════════════════════

COMBINED_PARSE_PROMPT = """You are Viraasat.ai's product intelligence engine.

Analyze the product photo and the artisan's voice description (text below). Extract ALL of the following into a single JSON object.

Voice description from artisan: "{voice_text}"
Artisan's craft category hint: "{craft_hint}"
Artisan's location: "{location}"

Return ONLY valid JSON with these exact keys:
{{
  "product_type": "specific product type (e.g., 'Tussar Silk Shawl', 'Blue Pottery Vase', 'Stainless Steel Water Bottle')",
  "materials": ["list of materials detected or mentioned"],
  "description": "2-3 sentence professional English product description for e-commerce",
  "heritage_story": "1-2 sentences about the craft tradition or brand story",
  "cultural_significance": "Why this craft/product matters — context",
  "crafting_time": "Estimated crafting time if applicable (e.g., '10 days')",
  "price_min": 0,
  "price_max": 0,
  "price_recommended": 0,
  "price_artisan_asked": 0,
  "seo_keywords": ["8-12 high-traffic search keywords for this product"],
  "features": ["5 key features/benefits of this product for e-commerce listing"],
  "unique_details": "What makes THIS specific piece unique (from photo + description)",
  "color_description": "Detailed color description for image generation prompts",
  "texture_description": "Detailed texture/material description for image generation",
  "background_suggestion": "Best studio background suggestion for this product type",
  "is_handcrafted": true,
  "lifestyle_setting": "The MOST natural real-life setting where someone would USE this product. Be specific. Examples: 'a gym bag on a bench in a modern fitness studio' for a water bottle, 'a marble vanity with warm lighting' for jewelry, 'a cozy reading nook with a wool throw' for a candle. This must match the ACTUAL product, not a generic setting.",
  "heritage_setting": "A setting that tells this product's ORIGIN STORY. For handcrafted items: the artisan workshop with relevant tools. For manufactured products: a premium brand showcase, factory floor, or the raw materials in nature. For a water bottle: 'pristine mountain stream with steel ore rocks'. For silk: 'a traditional loom workshop with silk threads'. Must be RELEVANT to THIS product.",
  "macro_focus_area": "The most visually interesting detail to zoom into for a macro shot. Be specific: 'the textured grip pattern on the bottle cap', 'the gold zari border thread work', 'the hand-hammered dimple pattern on brass surface'.",
  "description_amazon": "Product description formatted for Amazon (bullet points style)",
  "description_instagram": "Instagram caption with emojis and hashtags",
  "description_whatsapp": "Short WhatsApp-friendly description in Hindi + English mix"
}}

CRITICAL — Voice Description Extraction:
The artisan may speak in Hindi, Hinglish, or English. Extract ALL useful information:
- If they mention TIME spent making the product (e.g., "10 din laga", "ek hafte ka kaam"), put it in crafting_time.
- If they mention a PRICE they want (e.g., "500 rupaiye", "mai price 500 rakhna chahta", "teen sau"), put the numeric value in price_artisan_asked.
- If they describe materials in Hindi (e.g., "reshmi dhaga", "tamba", "chandi"), translate to English for materials list.
- If they mention the craft tradition or origin (e.g., "mere dada se sikha", "Jaipur ki kala"), use it in heritage_story.
- Common Hindi price words: sau=100, do sau=200, teen sau=300, paanch sau=500, hazaar=1000, do hazaar=2000.

CRITICAL for is_handcrafted: Set to true ONLY if the product is genuinely handmade/artisan-crafted. Set to false for factory-made, mass-produced, or branded manufactured products (like Cello, Milton, Prestige, etc.).

CRITICAL for lifestyle_setting and heritage_setting: These MUST be specific to the actual product type. Do NOT use generic "Indian artisan workshop" settings for manufactured products. Think about WHERE this product is actually used and WHERE it comes from.

For pricing: research similar products. Consider materials, crafting time, and skill level. Price should reflect fair value.

Be specific and detailed. The color_description, texture_description, and unique_details will be used directly in image generation prompts — make them vivid and precise.
"""


async def parse_and_enrich(
    product_image_bytes: bytes,
    voice_text: str = "",
    craft_hint: str = "",
    location: str = "",
) -> GeminiParsedOutput:
    """
    Single combined Gemini call: parse voice + analyze image + enrich + price + SEO.
    Returns structured data for the entire pipeline.
    """
    prompt = COMBINED_PARSE_PROMPT.format(
        voice_text=voice_text or "No voice description provided",
        craft_hint=craft_hint or "unknown",
        location=location or "India",
    )

    contents = [
        types.Part.from_bytes(data=product_image_bytes, mime_type="image/jpeg"),
        prompt,
    ]

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    # Strip markdown fences if present
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    data = json.loads(raw)

    # Sanitize fields that Gemini might return in unexpected types
    for key in ("price_min", "price_max", "price_recommended", "price_artisan_asked"):
        val = data.get(key)
        if val is None:
            data[key] = 0
        elif isinstance(val, str):
            cleaned = re.sub(r"[^\d.]", "", val)
            data[key] = float(cleaned) if cleaned else 0
    for key in ("materials", "seo_keywords", "features"):
        if not isinstance(data.get(key), list):
            data[key] = []
    for key in ("product_type", "description", "heritage_story", "cultural_significance",
                "crafting_time", "unique_details", "color_description", "texture_description",
                "background_suggestion", "lifestyle_setting", "heritage_setting",
                "macro_focus_area", "description_amazon", "description_instagram", "description_whatsapp"):
        if data.get(key) is None:
            data[key] = ""

    # Log key context fields for debugging
    logger.info(f"Parsed product: {data.get('product_type', '?')}")
    logger.info(f"  is_handcrafted: {data.get('is_handcrafted', '?')}")
    logger.info(f"  heritage_setting: {data.get('heritage_setting', '?')[:80]}")
    logger.info(f"  lifestyle_setting: {data.get('lifestyle_setting', '?')[:80]}")
    logger.info(f"  macro_focus_area: {data.get('macro_focus_area', '?')[:80]}")

    return GeminiParsedOutput(**data)


# ═══════════════════════════════════════════════════════════
# Auto-Crop Product from Background
# ═══════════════════════════════════════════════════════════

CROP_PROMPT = """Detect the main product in this photo. Return a JSON object with a bounding box:
{
  "box": [y_min, x_min, y_max, x_max]
}
Coordinates are normalized 0-1000 where 0=top/left edge, 1000=bottom/right edge.
The box should tightly contain the product with minimal background.
Return ONLY the JSON object."""


async def auto_crop_product(image_bytes: bytes) -> tuple[int, int, int, int]:
    """
    Use Gemini vision to detect the product bounding box.
    Returns (x1, y1, x2, y2) in pixel coordinates.
    """
    from PIL import Image

    img = Image.open(BytesIO(image_bytes))
    w, h = img.size

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            CROP_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    data = json.loads(raw)
    y_min, x_min, y_max, x_max = data["box"]

    # Convert normalized coords to pixels
    x1 = int(x_min * w / 1000)
    y1 = int(y_min * h / 1000)
    x2 = int(x_max * w / 1000)
    y2 = int(y_max * h / 1000)

    return (x1, y1, x2, y2)


# ═══════════════════════════════════════════════════════════
# A/B Testing Analysis
# ═══════════════════════════════════════════════════════════

AB_TEST_PROMPT = """You are an e-commerce conversion expert. Analyze these two product images (Variant A and Variant B) for an Indian artisan marketplace.

Score each variant 0-100 on:
1. Visual appeal and professionalism
2. Product clarity and detail visibility
3. Background cleanliness
4. Lighting quality
5. Likely click-through rate on Amazon/Flipkart

Return JSON:
{{
  "variant_a_score": 0,
  "variant_b_score": 0,
  "winner": "A" or "B",
  "confidence": 0.0 to 1.0,
  "reasoning": "Why the winner is better — specific, actionable feedback"
}}"""


async def ab_test_images(image_a_bytes: bytes, image_b_bytes: bytes) -> dict:
    """Compare two product images and pick the likely higher-converting one."""
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=[
            types.Part.from_bytes(data=image_a_bytes, mime_type="image/png"),
            types.Part.from_bytes(data=image_b_bytes, mime_type="image/png"),
            AB_TEST_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)
    return json.loads(raw)


# ═══════════════════════════════════════════════════════════
# Voice Intro Extraction (for onboarding)
# ═══════════════════════════════════════════════════════════

VOICE_INTRO_PROMPT = """An Indian artisan just introduced themselves via voice. Extract structured data from their speech.

Voice transcript: "{text}"

Return JSON:
{{
  "experience_years": null or integer,
  "heritage_generation": null or string like "5th generation",
  "story_snippet": "A brief 1-2 sentence story extracted from their words",
  "skills_mentioned": ["list of craft skills mentioned"],
  "materials_mentioned": ["list of materials mentioned"]
}}
Only include what was actually mentioned. Use null for missing fields."""


async def extract_voice_intro(transcript: str) -> dict:
    """Extract structured profile data from voice intro transcript."""
    prompt = VOICE_INTRO_PROMPT.format(text=transcript)
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
    return json.loads(raw)
