"""Viraasat.ai — Sharing & Distribution Router

Endpoints for WhatsApp, Instagram, landing pages, download kits, analytics.
"""

from __future__ import annotations

import json
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

import database as db
from config import OUTPUT_DIR, TEMPLATES_DIR
from models import ShareData, SharePlatform
from services.profile_service import get_profile
from services.heritage import get_heritage_info
from services.pillow_engine import create_brand_card, create_qr_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sharing", tags=["Sharing"])


# ═══════════════════════════════════════════════════════════
# Platform Share Data Generators
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/whatsapp", response_model=ShareData)
async def whatsapp_share(product_id: str):
    """Generate WhatsApp share data — caption + deep link."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    desc = product.get("description_json", {})
    caption = desc.get("description_whatsapp", "")
    if not caption:
        caption = (
            f"🏺 {desc.get('product_type', 'Handcrafted Product')}\n"
            f"{desc.get('description', '')}\n\n"
            f"💰 ₹{desc.get('price_recommended', 'Contact for price')}\n"
            f"✅ Verified on Viraasat.ai\n"
            f"🔗 viraasat.ai/p/{product_id[:8]}"
        )

    deep_link = f"https://wa.me/?text={quote(caption)}"

    card_files = [
        f"Viraasat_{ct}.png"
        for ct in ["hero", "features", "heritage", "macro", "lifestyle"]
        if (OUTPUT_DIR / product_id / f"Viraasat_{ct}.png").exists()
    ]

    return ShareData(
        platform="whatsapp",
        caption=caption,
        hashtags=[],
        image_paths=card_files,
        deep_link=deep_link,
    )


@router.get("/{product_id}/instagram", response_model=ShareData)
async def instagram_share(product_id: str):
    """Generate Instagram share data — caption + hashtags."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    desc = product.get("description_json", {})
    caption = desc.get("description_instagram", "")
    if not caption:
        seo = desc.get("seo_keywords", [])
        caption = (
            f"✨ {desc.get('product_type', 'Handcrafted Product')}\n\n"
            f"{desc.get('description', '')}\n\n"
            f"💰 Starting ₹{desc.get('price_recommended', '')}\n"
            f"🏺 Made by hand. Made with love.\n"
            f"📲 Link in bio\n\n"
        )

    hashtags = desc.get("seo_keywords", [])
    hashtags = [f"#{tag.replace(' ', '')}" for tag in hashtags]
    hashtags += ["#Viraasat", "#HandmadeIndia", "#ArtisanCraft", "#MadeInIndia"]

    card_files = [
        f"Viraasat_{ct}.png"
        for ct in ["hero", "lifestyle", "heritage", "macro", "features"]
        if (OUTPUT_DIR / product_id / f"Viraasat_{ct}.png").exists()
    ]

    return ShareData(
        platform="instagram",
        caption=caption + " ".join(hashtags[:20]),
        hashtags=hashtags[:20],
        image_paths=card_files,
    )


@router.get("/{product_id}/facebook", response_model=ShareData)
async def facebook_share(product_id: str):
    """Generate Facebook Marketplace share data."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    desc = product.get("description_json", {})
    caption = desc.get("description_amazon", "")
    if not caption:
        caption = desc.get("description", "Handcrafted product")

    return ShareData(
        platform="facebook",
        caption=caption,
        image_paths=[
            f"Viraasat_{ct}.png"
            for ct in ["hero", "features"]
            if (OUTPUT_DIR / product_id / f"Viraasat_{ct}.png").exists()
        ],
    )


# ═══════════════════════════════════════════════════════════
# Product Landing Page
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/landing-page", response_class=HTMLResponse)
async def landing_page(product_id: str):
    """Generate and serve a product landing page."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    artisan = await get_profile(product.get("artisan_id", ""))
    desc = product.get("description_json", {})

    # Load HTML template
    template_path = TEMPLATES_DIR / "landing_page.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _fallback_template()

    # Fill template
    html = template.replace("{{product_name}}", desc.get("product_type", "Handcrafted Product"))
    html = html.replace("{{description}}", desc.get("description", ""))
    html = html.replace("{{price}}", str(desc.get("price_recommended", "")))
    html = html.replace("{{price_min}}", str(desc.get("price_min", "")))
    html = html.replace("{{price_max}}", str(desc.get("price_max", "")))
    html = html.replace("{{heritage_story}}", desc.get("heritage_story", ""))
    html = html.replace("{{cultural_significance}}", desc.get("cultural_significance", ""))
    html = html.replace("{{materials}}", ", ".join(desc.get("materials", [])))
    html = html.replace("{{seo_keywords}}", ", ".join(desc.get("seo_keywords", [])))
    html = html.replace("{{product_id}}", product_id)
    html = html.replace("{{provenance_hash}}", product.get("provenance_hash", "")[:16])

    artisan_name = artisan.name if artisan else "Artisan"
    artisan_location = f"{artisan.district}, {artisan.state}" if artisan else "India"
    artisan_craft = artisan.craft_types[0] if artisan and artisan.craft_types else ""
    html = html.replace("{{artisan_name}}", artisan_name)
    html = html.replace("{{artisan_location}}", artisan_location)
    html = html.replace("{{artisan_craft}}", artisan_craft)
    html = html.replace("{{badge_level}}", artisan.badge_level if artisan else "new")

    # Features list
    features_html = ""
    for feat in desc.get("features", []):
        features_html += f"<li>{feat}</li>\n"
    html = html.replace("{{features_list}}", features_html)

    # UPI payment link
    upi_id = artisan.upi_id if artisan else ""
    if upi_id:
        upi_link = f"upi://pay?pa={upi_id}&pn={quote(artisan_name)}"
        if desc.get("price_recommended"):
            upi_link += f"&am={desc['price_recommended']}"
        html = html.replace("{{upi_link}}", upi_link)
    else:
        html = html.replace("{{upi_link}}", "#")

    return HTMLResponse(content=html)


# ═══════════════════════════════════════════════════════════
# Download Kit (all assets as ZIP)
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/download-kit")
async def download_kit(product_id: str):
    """Download all product assets as a ZIP file."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    product_dir = OUTPUT_DIR / product_id
    if not product_dir.exists():
        raise HTTPException(404, "Product files not found")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add card images
        for f in product_dir.iterdir():
            if f.suffix in (".png", ".jpg"):
                zf.write(str(f), f"images/{f.name}")

        # Add product info JSON
        desc = product.get("description_json", {})
        zf.writestr("product_info.json", json.dumps(desc, indent=2, ensure_ascii=False))

        # Add captions file
        captions = {
            "whatsapp": desc.get("description_whatsapp", ""),
            "instagram": desc.get("description_instagram", ""),
            "amazon": desc.get("description_amazon", ""),
        }
        zf.writestr("captions.json", json.dumps(captions, indent=2, ensure_ascii=False))

    buf.seek(0)
    filename = f"Viraasat_{product_id[:8]}_kit.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════
# Brand Card Download
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/brand-card")
async def brand_card(product_id: str):
    """Generate and download artisan brand card for this product."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    artisan = await get_profile(product.get("artisan_id", ""))
    if not artisan:
        raise HTTPException(404, "Artisan not found")

    card = create_brand_card(
        name=artisan.name,
        craft_type=artisan.craft_types[0] if artisan.craft_types else "",
        district=artisan.district,
        state=artisan.state,
        tagline=f"{artisan.badge_level.title()} Artisan",
        upi_id=artisan.upi_id or "",
        qr_data=f"https://viraasat.ai/artisan/{artisan.id[:8]}",
    )

    buf = BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


# ═══════════════════════════════════════════════════════════
# QR Scan Analytics
# ═══════════════════════════════════════════════════════════

@router.get("/{product_id}/analytics")
async def scan_analytics(product_id: str):
    """Get QR scan and view analytics for a product."""
    product = await db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")

    stats = await db.get_scan_stats(product_id)
    return {
        "product_id": product_id,
        **stats,
    }


@router.post("/{product_id}/scan")
async def record_qr_scan(
    product_id: str,
    action: str = "viewed",
):
    """Record a QR scan event."""
    import time
    await db.record_scan({
        "id": str(__import__("uuid").uuid4()),
        "product_id": product_id,
        "scanned_at": time.time(),
        "action_taken": action,
    })
    return {"status": "recorded"}


# ═══════════════════════════════════════════════════════════
# Fallback HTML Template
# ═══════════════════════════════════════════════════════════

def _fallback_template() -> str:
    """Minimal landing page template used when file template is missing."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{product_name}} — Viraasat.ai</title>
    <meta name="description" content="{{description}}">
    <meta name="keywords" content="{{seo_keywords}}">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f8f8f8; color: #122038; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .hero { text-align: center; padding: 40px 0; }
        .hero h1 { font-size: 2em; margin-bottom: 10px; }
        .price { font-size: 1.5em; color: #009688; font-weight: bold; }
        .section { background: white; border-radius: 12px; padding: 24px; margin: 16px 0; }
        .badge { display: inline-block; background: #D4AF37; color: #122038; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; }
        .btn { display: inline-block; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 8px; }
        .btn-upi { background: #009688; color: white; }
        .btn-wa { background: #25D366; color: white; }
        footer { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <span class="badge">✓ Verified on Viraasat.ai</span>
            <h1>{{product_name}}</h1>
            <p class="price">₹{{price}}</p>
            <p style="color:#666">Price range: ₹{{price_min}} — ₹{{price_max}}</p>
        </div>

        <div class="section">
            <h2>About This Product</h2>
            <p>{{description}}</p>
            <p><strong>Materials:</strong> {{materials}}</p>
        </div>

        <div class="section">
            <h2>Features</h2>
            <ul>{{features_list}}</ul>
        </div>

        <div class="section">
            <h2>Heritage & Story</h2>
            <p>{{heritage_story}}</p>
            <p><em>{{cultural_significance}}</em></p>
        </div>

        <div class="section">
            <h2>Meet the Artisan</h2>
            <p><strong>{{artisan_name}}</strong></p>
            <p>📍 {{artisan_location}}</p>
            <p>🏺 {{artisan_craft}}</p>
        </div>

        <div class="section" style="text-align:center">
            <a href="{{upi_link}}" class="btn btn-upi">💰 Pay via UPI</a>
            <a href="https://wa.me/?text=I'm interested in {{product_name}} on Viraasat.ai" class="btn btn-wa">💬 WhatsApp</a>
        </div>

        <div class="section" style="text-align:center; font-size:0.8em; color:#999">
            <p>Provenance ID: {{provenance_hash}}</p>
        </div>

        <footer>Powered by <strong>Viraasat.ai</strong> — Empowering India's artisans</footer>
    </div>
</body>
</html>"""
