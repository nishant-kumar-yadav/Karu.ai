"""Viraasat.ai — Image Generator Service

Approach: Inpainting — keep real product pixels, replace background.
Fallback: Full generation with strong reference constraints.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image, ImageFilter

from config import GEMINI_API_KEY, IMAGE_MODEL, FLASH_MODEL, OUTPUT_SIZE, PADDING_PX
from models import GeminiParsedOutput
from templates.prompts import get_filled_prompt, CARD_TYPES, CONSTRAINT_SUFFIX

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)


# ═══════════════════════════════════════════════════════════
# Inpainting: Keep product, replace background
# ═══════════════════════════════════════════════════════════

async def inpaint_background(
    product_image_bytes: bytes,
    background_prompt: str,
) -> Image.Image:
    """
    Send product photo + instructions to replace background only.
    The model keeps the product intact and generates a new background.
    """
    edit_prompt = (
        f"Keep the product in this photo EXACTLY as it is — same shape, color, texture, "
        f"every detail preserved pixel-perfect. ONLY replace the background with: "
        f"{background_prompt}. "
        f"Ensure seamless edge blending between product and new background. "
        f"The product must remain the sharp focal point. "
        f"Do NOT add any text, labels, or watermarks."
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=IMAGE_MODEL,
        contents=[
            types.Part.from_bytes(data=product_image_bytes, mime_type="image/jpeg"),
            edit_prompt,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )

    image_parts = [p for p in response.parts if p.inline_data]
    if not image_parts:
        raise RuntimeError("Inpainting returned no image")

    return Image.open(BytesIO(image_parts[0].inline_data.data))


# ═══════════════════════════════════════════════════════════
# Full Generation (fallback or lifestyle/heritage shots)
# ═══════════════════════════════════════════════════════════

async def generate_image(
    prompt: str,
    reference_image_bytes: bytes | None = None,
) -> Image.Image:
    """Generate an image from prompt, optionally with a reference photo."""
    contents = []
    if reference_image_bytes:
        contents.append(
            types.Part.from_bytes(data=reference_image_bytes, mime_type="image/jpeg")
        )
    contents.append(prompt)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )

    image_parts = [p for p in response.parts if p.inline_data]
    if not image_parts:
        raise RuntimeError("Image generation returned no image")

    return Image.open(BytesIO(image_parts[0].inline_data.data))


# ═══════════════════════════════════════════════════════════
# Post-Processing: Upscale + Sharpen
# ═══════════════════════════════════════════════════════════

def postprocess(img: Image.Image, size: tuple[int, int] = OUTPUT_SIZE) -> Image.Image:
    """Resize to target size with LANCZOS + subtle sharpen."""
    img = img.resize(size, Image.LANCZOS)
    img = img.filter(ImageFilter.SHARPEN)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# Generate All 5 Product Cards
# ═══════════════════════════════════════════════════════════

BACKGROUND_PROMPTS = {
    "hero": (
        "a seamless pure white studio background with soft, diffused lighting. "
        "Polished white surface with subtle reflection beneath the product."
    ),
    "features": (
        "a clean white studio background. MOVE the product to the far LEFT EDGE of the frame. "
        "The product must only occupy the leftmost 35%. The entire RIGHT 65% must be "
        "SOLID PURE WHITE — no shadows, no gradients, no floor reflections, nothing. "
        "Just blank white space on the right side for text overlay."
    ),
    "heritage": None,   # Full generation — contextual scene
    "macro": None,      # Full generation — macro close-up
    "lifestyle": None,  # Full generation — lifestyle scene
}


# Card presets by count: 3 → essentials, 4 → +lifestyle, 5 → all
CARD_PRESETS: dict[int, list[str]] = {
    3: ["hero", "features", "macro"],
    4: ["hero", "features", "macro", "lifestyle"],
    5: ["hero", "features", "macro", "lifestyle", "heritage"],
}


async def generate_all_cards(
    product_image_bytes: bytes,
    parsed: GeminiParsedOutput,
    category: str = "generic",
    num_cards: int = 5,
) -> dict[str, Image.Image]:
    """
    Generate product cards in parallel.
    num_cards: 3, 4, or 5 — controls which card types are generated.
    Returns dict of {card_type: PIL.Image}.
    """
    template_values = {
        "product_description": parsed.description or parsed.product_type,
        "material": ", ".join(parsed.materials) if parsed.materials else "premium material",
        "color_description": parsed.color_description or "rich, vibrant colors",
        "texture_description": parsed.texture_description or "fine detailed texture",
        "unique_details": parsed.unique_details or "intricate details",
        "lifestyle_setting": parsed.lifestyle_setting or "a modern, well-lit room with minimal decor",
        "heritage_setting": parsed.heritage_setting or "a premium brand showcase with elegant lighting",
        "macro_focus_area": parsed.macro_focus_area or parsed.texture_description or "the surface texture and material quality",
    }

    async def _gen_card(card_type: str) -> tuple[str, Image.Image]:
        bg = BACKGROUND_PROMPTS.get(card_type)

        if card_type == "hero":
            # Full generation — Gemini can restyle/arrange product beautifully
            prompt = get_filled_prompt(category, card_type, template_values)
            img = await generate_image(prompt, product_image_bytes)

        elif card_type == "features":
            # Inpainting — same product, space for overlays
            try:
                img = await inpaint_background(product_image_bytes, bg)
            except Exception as e:
                logger.warning(f"Inpainting failed for features, using full gen: {e}")
                prompt = get_filled_prompt(category, card_type, template_values)
                img = await generate_image(prompt, product_image_bytes)

        elif card_type == "macro":
            # Use the actual product photo enhanced — or generate macro
            prompt = get_filled_prompt(category, card_type, template_values)
            img = await generate_image(prompt, product_image_bytes)

        else:
            # Heritage & Lifestyle — full generation with reference
            prompt = get_filled_prompt(category, card_type, template_values)
            img = await generate_image(prompt, product_image_bytes)

        img = postprocess(img)
        return (card_type, img)

    # Select card types based on num_cards preset
    types_to_gen = CARD_PRESETS.get(num_cards, CARD_TYPES)
    tasks = [_gen_card(ct) for ct in types_to_gen]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    cards = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Card generation failed: {result}")
            continue
        card_type, img = result
        cards[card_type] = img

    return cards


# ═══════════════════════════════════════════════════════════
# Split Combined Image (legacy — from test.py prototype)
# ═══════════════════════════════════════════════════════════

LABEL_TO_CARD = {
    "hero_shot": "hero",
    "features_benefits": "features",
    "cutaway_stability": "heritage",
    "macro_focus": "macro",
    "complete_kit": "lifestyle",
}

DETECTION_PROMPT = """This image is a collage containing exactly 5 distinct e-commerce product images arranged together. Identify each sub-image and return a JSON array of exactly 5 objects.

Each object must have:
- "label": one of: "hero_shot", "features_benefits", "cutaway_stability", "macro_focus", "complete_kit"
- "box": [y_min, x_min, y_max, x_max] as integers 0-1000 (normalized)

Return ONLY the JSON array."""


async def split_combined_image(combined_img: Image.Image) -> dict[str, Image.Image]:
    """Split a combined collage image into 5 individual cards."""
    buf = BytesIO()
    combined_img.save(buf, format="PNG")
    combined_bytes = buf.getvalue()
    w, h = combined_img.size

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=FLASH_MODEL,
        contents=[
            types.Part.from_bytes(data=combined_bytes, mime_type="image/png"),
            DETECTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    boxes = json.loads(raw)
    cards = {}

    for b in boxes[:5]:
        label = b["label"]
        y_min, x_min, y_max, x_max = b["box"]

        x1 = max(0, int(x_min * w / 1000) - PADDING_PX)
        y1 = max(0, int(y_min * h / 1000) - PADDING_PX)
        x2 = min(w, int(x_max * w / 1000) + PADDING_PX)
        y2 = min(h, int(y_max * h / 1000) + PADDING_PX)

        cropped = combined_img.crop((x1, y1, x2, y2))
        cropped = postprocess(cropped)

        card_type = LABEL_TO_CARD.get(label, "hero")
        cards[card_type] = cropped

    return cards
