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
from fastapi.responses import FileResponse, StreamingResponse

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

    # ── Read + validate uploaded photos ──
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

    photo_bytes_list = []
    for photo in photos:
        if photo.content_type and photo.content_type not in ALLOWED_TYPES:
            raise HTTPException(400, f"Invalid file type '{photo.content_type}'. Only JPEG, PNG, WebP allowed.")
        data = await photo.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(400, f"File '{photo.filename}' too large ({len(data) // 1024 // 1024}MB). Max 10MB.")
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
    t_phase1 = time.time()
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
    logger.info(f"⏱️ Phase 1 (parse + heritage): {time.time() - t_phase1:.1f}s")

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

    # ── Phase 3: Image Generation + Trust Engine (parallelized) ──
    t_phase2 = time.time()
    clamped_cards = max(3, min(5, num_cards))
    image_task = generate_all_cards(
        product_image_bytes=primary_photo,
        parsed=parsed,
        category=category,
        num_cards=clamped_cards,
    )

    # Pre-compute trust score in parallel with images (saves ~7-15s)
    from services.trust_engine import compute_authenticity_score
    trust_task = compute_authenticity_score(
        profile=profile.model_dump(),
        parsed_data=parsed.model_dump(),
        product_image_bytes=primary_photo,
    )

    # Run image gen + price + trust in parallel
    cards_result, price_result, trust_result = await asyncio.gather(
        image_task, price_task, trust_task, return_exceptions=True
    )
    logger.info(f"⏱️ Phase 2 (images + price + trust): {time.time() - t_phase2:.1f}s")

    cards = cards_result if not isinstance(cards_result, Exception) else {}
    price_data = price_result if not isinstance(price_result, Exception) else {}
    trust_data = trust_result if not isinstance(trust_result, Exception) else None

    if isinstance(trust_result, Exception):
        logger.warning(f"Trust engine failed (will retry in enrich): {trust_result}")

    if isinstance(cards_result, Exception):
        logger.error(f"Image generation failed: {cards_result}")
        raise HTTPException(500, f"Image generation failed: {cards_result}")

    # Update parsed data with price info
    if isinstance(price_data, dict):
        parsed.price_min = price_data.get("min_price", 0)
        parsed.price_max = price_data.get("max_price", 0)
        parsed.price_recommended = price_data.get("recommended_price", 0)

    # ── Phase 4: Pillow Overlays (instant, CPU only) ──
    t_phase3 = time.time()
    # Use pre-computed trust score for overlays if available
    current_trust = trust_data["trust_score"] if trust_data else profile.trust_score
    provenance_hash = generate_provenance_hash(
        artisan_id=artisan_id,
        product_image_bytes=primary_photo,
        trust_score=current_trust,
    )

    qr_data = f"https://viraasat.ai/verify/{provenance_hash[:16]}"

    final_cards = apply_overlays(
        cards=cards,
        parsed_data=parsed.model_dump(),
        artisan_name=profile.name,
        craft_type=category,
        region=location,
        qr_data=qr_data,
        trust_score=current_trust,
    )
    logger.info(f"⏱️ Phase 3 (overlays): {time.time() - t_phase3:.1f}s")

    # ── Phase 5: Save original photos to disk ──
    original_filenames = []
    for i, photo_data in enumerate(photo_bytes_list):
        photo_filename = f"original_{i}.jpg"
        photo_path = product_dir / photo_filename
        with open(str(photo_path), "wb") as f:
            f.write(photo_data)
        original_filenames.append(photo_filename)

    # ── Phase 6: Save generated cards + metadata ──
    saved_cards = []
    for card_type, img in final_cards.items():
        filename = f"Viraasat_{card_type}.png"
        filepath = product_dir / filename
        img.save(str(filepath), "PNG")

        # Compliance check — only meaningful for hero card (e-commerce listing)
        # Other cards (heritage, lifestyle, macro) intentionally have non-white backgrounds
        if card_type == "hero":
            compliance = check_compliance(img)
            status = "✓ Platform Ready" if compliance["platform_ready"] else "⚠ Check issues"
        else:
            status = "✓ Ready"

        saved_cards.append(GeneratedCard(
            card_type=card_type,
            filename=filename,
            description=f"{card_type.title()} card — {status}",
        ))

    # ── Phase 7: Save to DB + enrich profile ──
    product_data = {
        "id": product_id,
        "artisan_id": artisan_id,
        "product_type": parsed.product_type,
        "materials": parsed.materials,
        "description_json": parsed.model_dump(),
        "original_photos": original_filenames,
        "generated_images": [c.filename for c in saved_cards],
        "trust_score": current_trust,
        "provenance_hash": provenance_hash,
        "price_suggested": parsed.price_recommended,
        "seo_keywords": parsed.seo_keywords,
        "created_at": time.time(),
    }
    await db.create_product(product_data)

    # Auto-enrich artisan profile (pass pre-computed trust to skip re-calling Gemini)
    from PIL import Image
    primary_img = Image.open(BytesIO(primary_photo))
    updated_profile = await enrich_profile_from_product(
        artisan_id, parsed.model_dump(), primary_img,
        product_image_bytes=primary_photo,
        pre_computed_trust=trust_data,
    )

    elapsed = round(time.time() - start, 1)

    return ProductResponse(
        product_id=product_id,
        artisan_id=artisan_id,
        cards=saved_cards,
        parsed_data=parsed,
        provenance_hash=provenance_hash,
        trust_score=updated_profile.trust_score,
        processing_time_seconds=elapsed,
    )


# ═══════════════════════════════════════════════════════════
# Progressive Generation (SSE Streaming)
# ═══════════════════════════════════════════════════════════

@router.post("/generate-stream")
async def generate_product_stream(
    artisan_id: str = Form(...),
    voice_description: str = Form(""),
    product_type: str = Form(""),
    preferred_language: str = Form("hi"),
    num_cards: int = Form(3),
    photos: list[UploadFile] = File(...),
):
    """Streaming version of /generate using SSE (Server-Sent Events)."""
    import json
    
    async def sse_generator():
        try:
            profile = await get_profile(artisan_id)
            if not profile:
                yield f"data: {{ \"error\": \"Artisan not found\" }}\n\n"
                return

            yield f"data: {json.dumps({'event': 'status', 'message': 'Analyzing product imagery and voice concepts...'})}\n\n"

            MAX_FILE_SIZE = 10 * 1024 * 1024
            photo_bytes_list = []
            for photo in photos:
                data = await photo.read()
                photo_bytes_list.append(data)
                
            primary_photo = photo_bytes_list[0]
            product_id = str(uuid.uuid4())
            product_dir = OUTPUT_DIR / product_id
            product_dir.mkdir(parents=True, exist_ok=True)
            
            category = profile.craft_types[0] if profile.craft_types else "generic"
            location = f"{profile.district}, {profile.state}"

            parse_task = parse_and_enrich(
                product_image_bytes=primary_photo,
                voice_text=voice_description,
                craft_hint=category,
                location=location,
            )
            heritage_task = get_heritage_info(
                craft_type=category,
                district=profile.district,
                state=profile.state,
                product_type=product_type,
                artisan_story=profile.heritage_story or "",
            )
            
            parsed, heritage_data = await asyncio.gather(parse_task, heritage_task, return_exceptions=True)
            if isinstance(parsed, Exception):
                parsed = GeminiParsedOutput(
                    product_type=product_type or "Handcrafted Product",
                    description=voice_description or "Beautiful handcrafted product",
                )
            heritage = heritage_data if not isinstance(heritage_data, Exception) else {}
            if isinstance(heritage, dict):
                if not parsed.heritage_story and heritage.get("origin_story"):
                    parsed.heritage_story = heritage["origin_story"]
                if not parsed.cultural_significance and heritage.get("cultural_significance"):
                    parsed.cultural_significance = heritage["cultural_significance"]

            yield f"data: {json.dumps({'event': 'parsed', 'data': parsed.model_dump()})}\n\n"
            yield f"data: {json.dumps({'event': 'status', 'message': 'Evaluating authenticity and pricing...'})}\n\n"

            price_task = get_price_advice(
                product_type=parsed.product_type,
                materials=parsed.materials,
                crafting_time=parsed.crafting_time,
                region=location,
                asked_price=parsed.price_artisan_asked or 0,
                is_handcrafted=parsed.is_handcrafted,
            )
            from services.trust_engine import compute_authenticity_score
            trust_task = compute_authenticity_score(
                profile=profile.model_dump(),
                parsed_data=parsed.model_dump(),
                product_image_bytes=primary_photo,
            )
            
            price_data, trust_data = await asyncio.gather(price_task, trust_task, return_exceptions=True)
            
            if isinstance(price_data, dict):
                parsed.price_min = price_data.get("min_price", 0)
                parsed.price_max = price_data.get("max_price", 0)
                parsed.price_recommended = price_data.get("recommended_price", 0)
            yield f"data: {json.dumps({'event': 'price', 'data': price_data if isinstance(price_data, dict) else {}})}\n\n"

            current_trust = trust_data["trust_score"] if trust_data and not isinstance(trust_data, Exception) else profile.trust_score
            yield f"data: {json.dumps({'event': 'trust', 'score': current_trust})}\n\n"
            yield f"data: {json.dumps({'event': 'status', 'message': 'Generating high-fidelity studio imagery...'})}\n\n"

            original_filenames = []
            for i, photo_data in enumerate(photo_bytes_list):
                photo_filename = f"original_{i}.jpg"
                photo_path = product_dir / photo_filename
                with open(str(photo_path), "wb") as f:
                    f.write(photo_data)
                original_filenames.append(photo_filename)

            provenance_hash = generate_provenance_hash(artisan_id=artisan_id, product_image_bytes=primary_photo, trust_score=current_trust)
            qr_data = f"https://viraasat.ai/verify/{provenance_hash[:16]}"

            from services.image_generator import generate_cards_streaming
            clamped_cards = max(3, min(5, num_cards))
            stream = generate_cards_streaming(
                product_image_bytes=primary_photo,
                parsed=parsed,
                category=category,
                num_cards=clamped_cards,
            )
            
            saved_cards = []
            async for card_type, img in stream:
                overlayed = apply_overlays(
                    cards={card_type: img},
                    parsed_data=parsed.model_dump(),
                    artisan_name=profile.name,
                    craft_type=category,
                    region=location,
                    qr_data=qr_data,
                    trust_score=current_trust,
                )
                final_img = overlayed.get(card_type, img)
                filename = f"Viraasat_{card_type}.png"
                filepath = product_dir / filename
                final_img.save(str(filepath), "PNG")
                
                saved_cards.append(GeneratedCard(card_type=card_type, filename=filename, description=f"{card_type.title()} card"))
                yield f"data: {json.dumps({'event': 'card', 'card_type': card_type, 'url': f'/products/{product_id}/card/{card_type}'})}\n\n"

            product_data = {
                "id": product_id,
                "artisan_id": artisan_id,
                "product_type": parsed.product_type,
                "materials": parsed.materials,
                "description_json": parsed.model_dump(),
                "original_photos": original_filenames,
                "generated_images": [c.filename for c in saved_cards],
                "trust_score": current_trust,
                "provenance_hash": provenance_hash,
                "price_suggested": parsed.price_recommended,
                "seo_keywords": parsed.seo_keywords,
                "created_at": time.time(),
            }
            await db.create_product(product_data)
            
            yield f"data: {json.dumps({'event': 'complete', 'product_id': product_id})}\n\n"

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


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
