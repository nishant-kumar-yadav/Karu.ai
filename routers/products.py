"""Viraasat.ai — Products Router

Main endpoint: /generate — the full pipeline.
Photos + voice → AI parse → image gen → Pillow overlays → QR → save.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

import database as db
from config import OUTPUT_DIR
from models import ProductResponse, GeneratedCard, GeminiParsedOutput, ABTestResult
from services.ai_pipeline import parse_and_enrich, ab_test_images
from services.image_generator import generate_all_cards
from services.pillow_engine import (
    apply_overlays, generate_provenance_hash, check_compliance,
    create_brand_card, add_qr_overlay,
)
from services.price_advisor import get_price_advice
from services.heritage import get_heritage_info
from services.profile_service import get_profile, enrich_profile_from_product

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


# ═══════════════════════════════════════════════════════════
# Main Generation Pipeline
# ═══════════════════════════════════════════════════════════

@router.post("/generate", response_model=ProductResponse)
async def generate_product(
    artisan_id: str = Form(...),
    voice_description: str = Form(""),
    product_type: str = Form(""),
    preferred_language: str = Form("hi"),
    num_cards: int = Form(3),
    photos: list[UploadFile] = File(...),
):
    """
    THE core pipeline:
    1. Read photos
    2. AI parse + enrich (combined Gemini call)
    3. Generate 5 product card images (inpainting + generation)
    4. Apply Pillow text overlays
    5. Generate QR + provenance hash
    6. Save everything + update profile

    Parallelization strategy:
    - Parse + crop run while images are being read
    - Heritage + price advisor run in parallel with image generation
    - Pillow overlays are instant (CPU, no API)
    """
    start = time.time()

    # ── Validate artisan ──
    profile = await get_profile(artisan_id)
    if not profile:
        raise HTTPException(404, "Artisan not found")

    # ── Read uploaded photos ──
    photo_bytes_list = []
    for photo in photos:
        data = await photo.read()
        photo_bytes_list.append(data)

    if not photo_bytes_list:
        raise HTTPException(400, "At least one photo required")

    primary_photo = photo_bytes_list[0]
    product_id = str(uuid.uuid4())
    product_dir = OUTPUT_DIR / product_id
    product_dir.mkdir(parents=True, exist_ok=True)

    # ── Determine craft category ──
    category = profile.craft_types[0] if profile.craft_types else "generic"
    location = f"{profile.district}, {profile.state}"

    # ── Phase 1: AI Parse + Enrich (parallel with heritage + price) ──
    parse_task = parse_and_enrich(
        product_image_bytes=primary_photo,
        voice_text=voice_description,
        craft_hint=category,
        location=location,
    )

    # Heritage and price run in parallel with parsing
    heritage_task = get_heritage_info(
        craft_type=category,
        district=profile.district,
        state=profile.state,
        product_type=product_type,
        artisan_story=profile.heritage_story or "",
    )

    parsed, heritage_data = await asyncio.gather(
        parse_task, heritage_task, return_exceptions=True
    )

    # Handle parse failures
    if isinstance(parsed, Exception):
        logger.error(f"Parse failed: {type(parsed).__name__}: {parsed}")
        parsed = GeminiParsedOutput(
            product_type=product_type or "Handcrafted Product",
            description=voice_description or "Beautiful handcrafted product",
        )

    heritage = heritage_data if not isinstance(heritage_data, Exception) else {}

    # Enrich parsed data with heritage
    if isinstance(heritage, dict):
        if not parsed.heritage_story and heritage.get("origin_story"):
            parsed.heritage_story = heritage["origin_story"]
        if not parsed.cultural_significance and heritage.get("cultural_significance"):
            parsed.cultural_significance = heritage["cultural_significance"]

    # ── Phase 2: Price Advisor (can run after parse) ──
    asked_price = parsed.price_artisan_asked or 0
    price_task = get_price_advice(
        product_type=parsed.product_type,
        materials=parsed.materials,
        crafting_time=parsed.crafting_time,
        region=location,
        asked_price=asked_price,
        is_handcrafted=parsed.is_handcrafted,
    )

    # ── Phase 3: Image Generation (the slow part — parallelized) ──
    clamped_cards = max(3, min(5, num_cards))
    image_task = generate_all_cards(
        product_image_bytes=primary_photo,
        parsed=parsed,
        category=category,
        num_cards=clamped_cards,
    )

    # Run image gen + price in parallel
    cards_result, price_result = await asyncio.gather(
        image_task, price_task, return_exceptions=True
    )

    cards = cards_result if not isinstance(cards_result, Exception) else {}
    price_data = price_result if not isinstance(price_result, Exception) else {}

    if isinstance(cards_result, Exception):
        logger.error(f"Image generation failed: {cards_result}")
        raise HTTPException(500, f"Image generation failed: {cards_result}")

    # Update parsed data with price info
    if isinstance(price_data, dict):
        parsed.price_min = price_data.get("min_price", 0)
        parsed.price_max = price_data.get("max_price", 0)
        parsed.price_recommended = price_data.get("recommended_price", 0)

    # ── Phase 4: Pillow Overlays (instant, CPU only) ──
    provenance_hash = generate_provenance_hash(
        artisan_id=artisan_id,
        product_image_bytes=primary_photo,
        trust_score=profile.trust_score,
    )

    qr_data = f"https://viraasat.ai/verify/{provenance_hash[:16]}"

    final_cards = apply_overlays(
        cards=cards,
        parsed_data=parsed.model_dump(),
        artisan_name=profile.name,
        craft_type=category,
        region=location,
        qr_data=qr_data,
        trust_score=profile.trust_score,
    )

    # ── Phase 5: Save images + metadata ──
    saved_cards = []
    for card_type, img in final_cards.items():
        filename = f"Viraasat_{card_type}.png"
        filepath = product_dir / filename
        img.save(str(filepath), "PNG")

        # Compliance check
        compliance = check_compliance(img)

        saved_cards.append(GeneratedCard(
            card_type=card_type,
            filename=filename,
            description=f"{card_type.title()} card — {'✓ Platform Ready' if compliance['platform_ready'] else '⚠ Check issues'}",
        ))

    # ── Phase 6: Save to DB + enrich profile ──
    product_data = {
        "id": product_id,
        "artisan_id": artisan_id,
        "product_type": parsed.product_type,
        "materials": parsed.materials,
        "description_json": parsed.model_dump(),
        "original_photos": [f"photo_{i}.jpg" for i in range(len(photo_bytes_list))],
        "generated_images": [c.filename for c in saved_cards],
        "trust_score": profile.trust_score,
        "provenance_hash": provenance_hash,
        "price_suggested": parsed.price_recommended,
        "seo_keywords": parsed.seo_keywords,
        "created_at": time.time(),
    }
    await db.create_product(product_data)

    # Auto-enrich artisan profile
    from PIL import Image
    primary_img = Image.open(BytesIO(primary_photo))
    await enrich_profile_from_product(artisan_id, parsed.model_dump(), primary_img)

    elapsed = round(time.time() - start, 1)

    return ProductResponse(
        product_id=product_id,
        artisan_id=artisan_id,
        cards=saved_cards,
        parsed_data=parsed,
        provenance_hash=provenance_hash,
        trust_score=profile.trust_score,
        processing_time_seconds=elapsed,
    )


# ═══════════════════════════════════════════════════════════
# Get Product Details
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get product details and card metadata."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.get("/artisan/{artisan_id}")
async def list_artisan_products(artisan_id: str):
    """List all products for an artisan."""
    products = await db.get_products_by_artisan(artisan_id)
    return {"artisan_id": artisan_id, "products": products, "count": len(products)}


# ═══════════════════════════════════════════════════════════
# Get Generated Card Image
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/card/{card_type}")
async def get_card_image(product_id: str, card_type: str):
    """Serve a generated card image."""
    filepath = OUTPUT_DIR / product_id / f"Viraasat_{card_type}.png"
    if not filepath.exists():
        raise HTTPException(404, "Card image not found")
    return FileResponse(str(filepath), media_type="image/png")


# ═══════════════════════════════════════════════════════════
# A/B Testing
# ═══════════════════════════════════════════════════════════

@router.post("/{product_id}/ab-test", response_model=ABTestResult)
async def ab_test(
    product_id: str,
    variant_a: UploadFile = File(...),
    variant_b: UploadFile = File(...),
):
    """Compare two product images for conversion potential."""
    a_bytes = await variant_a.read()
    b_bytes = await variant_b.read()

    result = await ab_test_images(a_bytes, b_bytes)

    return ABTestResult(
        winner=result.get("winner", "A"),
        confidence=result.get("confidence", 0.5),
        reasoning=result.get("reasoning", ""),
        variant_a_score=result.get("variant_a_score", 50),
        variant_b_score=result.get("variant_b_score", 50),
    )


# ═══════════════════════════════════════════════════════════
# Price Advisor (standalone endpoint)
# ═══════════════════════════════════════════════════════════

@router.post("/{product_id}/price-advice")
async def price_advice(product_id: str):
    """Get price advice for an existing product."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    desc = product.get("description_json", {})
    result = await get_price_advice(
        product_type=desc.get("product_type", ""),
        materials=desc.get("materials", []),
        crafting_time=desc.get("crafting_time", ""),
    )
    return result


# ═══════════════════════════════════════════════════════════
# Negotiation Coach
# ═══════════════════════════════════════════════════════════

@router.post("/{product_id}/negotiate")
async def negotiation_coach(
    product_id: str,
    message: str = Form(...),
):
    """Get negotiation coaching for a product price discussion."""
    from services.price_advisor import negotiate

    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    desc = product.get("description_json", {})
    result = await negotiate(
        artisan_message=message,
        product_type=desc.get("product_type", ""),
        price_min=desc.get("price_min", 0),
        price_max=desc.get("price_max", 0),
        recommended=desc.get("price_recommended", 0),
    )
    return result
