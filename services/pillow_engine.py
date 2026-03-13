"""Viraasat.ai — Pillow Engine

Handles ALL text overlays, QR codes, monograms, brand cards, catalog pages.
Code-rendered text = 100% crisp, consistent, instant.
"""

from __future__ import annotations

import hashlib
import logging
import math
from io import BytesIO
from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    FONTS_DIR, FONT_BOLD, FONT_REGULAR, FONT_SEMIBOLD,
    NAVY, WHITE, TEAL, GOLD, LIGHT_GRAY, OUTPUT_SIZE,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Font Helpers
# ═══════════════════════════════════════════════════════════

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if file not found."""
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        logger.warning(f"Font not found: {path}, using default")
        return ImageFont.load_default()


def font_bold(size: int) -> ImageFont.FreeTypeFont:
    return _load_font(FONT_BOLD, size)


def font_regular(size: int) -> ImageFont.FreeTypeFont:
    return _load_font(FONT_REGULAR, size)


def font_semibold(size: int) -> ImageFont.FreeTypeFont:
    return _load_font(FONT_SEMIBOLD, size)


def _truncate_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate text with ellipsis if it exceeds max_width pixels."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    while len(text) > 3:
        text = text[:-1]
        bbox = draw.textbbox((0, 0), text + "...", font=font)
        if bbox[2] - bbox[0] <= max_width:
            return text + "..."
    return text + "..."


def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 2) -> list[str]:
    """Word-wrap text into multiple lines, truncating the last line if needed."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if len(lines) < max_lines:
        lines.append(current)
    # Truncate last line if we ran out of room
    if len(lines) == max_lines:
        leftover_words = words[len(" ".join(lines).split()):]
        if leftover_words:
            lines[-1] = _truncate_text(draw, lines[-1] + " " + " ".join(leftover_words), font, max_width)
    return lines


# ═══════════════════════════════════════════════════════════
# Card 1: Hero Shot — No overlays (clean image)
# ═══════════════════════════════════════════════════════════

def create_hero_card(base_image: Image.Image) -> Image.Image:
    """Hero shot — clean image with subtle bottom brand bar."""
    img = base_image.copy().convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Thin teal line at bottom
    draw.rectangle([(0, h - 6), (w, h)], fill=(*TEAL, 200))

    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# Card 2: Features & Benefits — Solid Panel Layout
# ═══════════════════════════════════════════════════════════

# Accent colors for each feature bullet (cycling teal/gold/navy)
_BULLET_COLORS = [
    (0, 150, 136),    # teal
    (212, 175, 55),   # gold
    (18, 32, 56),     # navy
    (0, 150, 136),    # teal
    (212, 175, 55),   # gold
]


def create_features_card(
    base_image: Image.Image,
    title: str = "PREMIUM FEATURES",
    features: list[str] | None = None,
) -> Image.Image:
    """
    Professional feature card: product on left, solid white panel on right.
    Clean typography, colored bullet accents, no amateur icons.
    """
    img = base_image.copy().convert("RGB")
    w, h = img.size

    # ── Step 1: Create solid white right panel ──
    # This COVERS the right 55% completely — clean white canvas for text
    panel_x = int(w * 0.42)
    # Soft gradient edge: blend from image to white over ~3% width
    blend_start = panel_x - int(w * 0.03)
    blend_end = panel_x

    # Draw white panel
    panel = Image.new("RGB", (w - blend_start, h), (255, 255, 255))
    # Create alpha mask for smooth blend
    mask = Image.new("L", (w - blend_start, h), 255)
    mask_draw = ImageDraw.Draw(mask)
    blend_width = blend_end - blend_start
    for x_off in range(blend_width):
        alpha = int(255 * (x_off / blend_width))
        mask_draw.line([(x_off, 0), (x_off, h)], fill=alpha)
    img.paste(panel, (blend_start, 0), mask)

    draw = ImageDraw.Draw(img)

    # ── Step 2: Title — bold, dark, top of white area ──
    text_left = panel_x + int(w * 0.03)
    text_right = w - int(w * 0.04)
    title_max_w = text_right - text_left

    title_font = font_bold(int(h * 0.036))
    truncated_title = _truncate_text(draw, title.upper(), title_font, title_max_w)
    title_y = int(h * 0.06)
    draw.text(
        (text_left, title_y),
        truncated_title,
        fill=NAVY,
        font=title_font,
    )

    # Thin teal underline below title
    title_bbox = draw.textbbox((text_left, title_y), truncated_title, font=title_font)
    line_y = title_bbox[3] + int(h * 0.015)
    draw.line(
        [(text_left, line_y), (text_left + int(w * 0.12), line_y)],
        fill=TEAL,
        width=3,
    )

    # ── Step 3: Feature items — clean bullets + wrapped text ──
    if not features:
        features = ["Premium Quality", "Handcrafted", "Durable", "Authentic", "Eco-Friendly"]

    num_features = min(len(features), 5)

    feat_area_top = line_y + int(h * 0.035)
    feat_area_bottom = int(h * 0.92)
    total_feat_h = feat_area_bottom - feat_area_top
    slot_h = total_feat_h // num_features

    feat_font = font_regular(int(h * 0.025))
    feat_line_h = int(h * 0.033)
    bullet_r = int(h * 0.010)  # small clean circle

    for i, feature in enumerate(features[:num_features]):
        slot_top = feat_area_top + i * slot_h
        slot_cy = slot_top + slot_h // 2

        # ── Colored bullet circle ──
        bullet_cx = text_left + bullet_r
        bullet_cy = slot_cy
        bullet_color = _BULLET_COLORS[i % len(_BULLET_COLORS)]
        draw.ellipse(
            [(bullet_cx - bullet_r, bullet_cy - bullet_r),
             (bullet_cx + bullet_r, bullet_cy + bullet_r)],
            fill=bullet_color,
        )

        # ── Feature text — word-wrapped, up to 3 lines ──
        ft_x = bullet_cx + bullet_r + int(w * 0.02)
        max_text_w = text_right - ft_x
        lines = _wrap_text(draw, feature, feat_font, max_text_w, max_lines=3)

        text_block_h = len(lines) * feat_line_h
        text_y = bullet_cy - text_block_h // 2

        for j, line in enumerate(lines):
            draw.text(
                (ft_x, text_y + j * feat_line_h),
                line,
                fill=(40, 40, 50),  # dark charcoal, not harsh black
                font=feat_font,
            )

        # ── Subtle separator line between features ──
        if i < num_features - 1:
            sep_y = slot_top + slot_h - 1
            draw.line(
                [(text_left, sep_y), (text_right, sep_y)],
                fill=(230, 230, 230),
                width=1,
            )

    # ── Step 4: Bottom branding ──
    brand_font = font_semibold(int(h * 0.016))
    brand_text = "VIRAASAT.AI"
    draw.text(
        (text_left, int(h * 0.95)),
        brand_text,
        fill=TEAL,
        font=brand_font,
    )

    return img


# ═══════════════════════════════════════════════════════════
# Card 3: Heritage / Process Labels
# ═══════════════════════════════════════════════════════════

def create_heritage_card(
    base_image: Image.Image,
    heritage_text: str = "",
    craft_type: str = "",
    region: str = "",
) -> Image.Image:
    """Add bold heritage story overlay at the bottom of a lifestyle image."""
    img = base_image.copy().convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Strong bottom gradient bar (navy)
    bar_y = int(h * 0.62)
    for y in range(bar_y, h):
        progress = (y - bar_y) / (h - bar_y)
        alpha = min(240, int(progress * progress * 240))
        draw.line([(0, y), (w, y)], fill=(18, 32, 56, alpha))

    # Gold accent line at top of gradient
    draw.line([(40, int(h * 0.70)), (w - 40, int(h * 0.70))], fill=(*GOLD, 200), width=3)

    # Heritage badge (gold pill)
    badge_font = font_bold(int(h * 0.028))
    badge_text = f"  {craft_type.upper() or 'HERITAGE CRAFT'}  "
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = bbox[2] - bbox[0] + 30
    draw.rounded_rectangle(
        [(40, int(h * 0.72)), (40 + badge_w, int(h * 0.77))],
        radius=14,
        fill=(*GOLD, 240),
    )
    draw.text(
        (55, int(h * 0.725)),
        badge_text,
        fill=(*NAVY, 255),
        font=badge_font,
    )

    # Region — large, white
    region_font = font_semibold(int(h * 0.038))
    draw.text(
        (40, int(h * 0.79)),
        region or "Premium Quality Product",
        fill=(*WHITE, 255),
        font=region_font,
    )

    # Heritage story text
    if heritage_text:
        story_font = font_regular(int(h * 0.026))
        words = heritage_text.split()
        lines = []
        current = ""
        for word in words:
            if len(current + " " + word) > 45:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            lines.append(current)

        for i, line in enumerate(lines[:3]):
            draw.text(
                (40, int(h * 0.86) + i * int(h * 0.035)),
                line,
                fill=(*WHITE, 220),
                font=story_font,
            )

    # Bottom-right: Viraasat branding
    vir_font = font_bold(int(h * 0.02))
    draw.text(
        (w - 200, h - int(h * 0.045)),
        "VIRAASAT.AI",
        fill=(*GOLD, 140),
        font=vir_font,
    )

    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# Card 4: Macro / Texture Label
# ═══════════════════════════════════════════════════════════

def create_macro_card(
    base_image: Image.Image,
    texture_label: str = "HANDCRAFTED DETAIL",
    material: str = "",
) -> Image.Image:
    """Add a bold texture/material label on a macro shot."""
    img = base_image.copy().convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bottom-left frosted panel
    panel_w = int(w * 0.55)
    panel_h = int(h * 0.14)
    panel_y = h - panel_h - 30
    draw.rounded_rectangle(
        [(30, panel_y), (30 + panel_w, panel_y + panel_h)],
        radius=18,
        fill=(*NAVY, 210),
    )
    # Gold accent on top of panel
    draw.line(
        [(40, panel_y + 4), (30 + panel_w - 10, panel_y + 4)],
        fill=(*GOLD, 255), width=3,
    )

    # Main label — truncate to fit panel
    label_font = font_bold(int(h * 0.032))
    label_max_w = panel_w - 50
    label_text = _truncate_text(draw, texture_label.upper(), label_font, label_max_w)
    draw.text(
        (55, panel_y + int(panel_h * 0.18)),
        label_text,
        fill=(*WHITE, 255),
        font=label_font,
    )

    # Sub-label (material) — also truncated
    if material:
        sub_font = font_regular(int(h * 0.022))
        mat_text = _truncate_text(draw, material, sub_font, label_max_w)
        draw.text(
            (55, panel_y + int(panel_h * 0.58)),
            mat_text,
            fill=(*TEAL, 240),
            font=sub_font,
        )

    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# Card 5: Lifestyle — Brand Overlay
# ═══════════════════════════════════════════════════════════

def create_lifestyle_card(
    base_image: Image.Image,
    brand_name: str = "VIRAASAT",
    tagline: str = "",
) -> Image.Image:
    """Add bold brand overlay on lifestyle shot — top bar + bottom brand strip."""
    img = base_image.copy().convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Top navy strip with artisan name
    draw.rectangle([(0, 0), (w, int(h * 0.09))], fill=(*NAVY, 220))
    draw.rectangle([(0, int(h * 0.09)), (w, int(h * 0.09) + 4)], fill=(*GOLD, 255))
    name_font = font_bold(int(h * 0.035))
    draw.text(
        (30, int(h * 0.025)),
        brand_name.upper(),
        fill=(*WHITE, 255),
        font=name_font,
    )

    # Tagline next to name (if fits)
    if tagline:
        tag_font = font_regular(int(h * 0.022))
        # Right-align tagline
        bbox = draw.textbbox((0, 0), tagline, font=tag_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (w - tw - 30, int(h * 0.035)),
            tagline,
            fill=(*GOLD, 220),
            font=tag_font,
        )

    # Bottom brand strip
    draw.rectangle([(0, int(h * 0.92)), (w, h)], fill=(*NAVY, 200))
    draw.rectangle([(0, int(h * 0.92) - 3), (w, int(h * 0.92))], fill=(*TEAL, 255))

    vir_font = font_bold(int(h * 0.025))
    draw.text(
        (30, int(h * 0.94)),
        "VIRAASAT.AI  ·  One-Tap Digital Agency",
        fill=(*WHITE, 200),
        font=vir_font,
    )

    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# QR Code Generation
# ═══════════════════════════════════════════════════════════

def generate_provenance_hash(
    artisan_id: str,
    product_image_bytes: bytes,
    trust_score: float,
) -> str:
    """Generate SHA-256 provenance hash."""
    from datetime import datetime
    data = f"{artisan_id}|{len(product_image_bytes)}|{datetime.utcnow().isoformat()}|{trust_score}"
    return hashlib.sha256(data.encode()).hexdigest()


def create_qr_code(
    data: str,
    size: int = 300,
    fill_color: str = "#122038",
    back_color: str = "white",
) -> Image.Image:
    """Generate a QR code image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img.resize((size, size), Image.LANCZOS).convert("RGBA")


def add_qr_overlay(
    card_image: Image.Image,
    qr_data: str,
    position: str = "bottom-right",
    qr_size: int = 180,
) -> Image.Image:
    """Overlay a QR code on a product card."""
    img = card_image.copy().convert("RGBA")
    w, h = img.size

    qr_img = create_qr_code(qr_data, size=qr_size)

    # Add white border around QR
    bordered = Image.new("RGBA", (qr_size + 20, qr_size + 20), (255, 255, 255, 240))
    bordered.paste(qr_img, (10, 10))

    positions = {
        "bottom-right": (w - qr_size - 50, h - qr_size - 50),
        "bottom-left": (30, h - qr_size - 50),
        "top-right": (w - qr_size - 50, 30),
    }
    pos = positions.get(position, positions["bottom-right"])

    img.paste(bordered, pos, bordered)
    return img.convert("RGB")


# ═══════════════════════════════════════════════════════════
# Monogram Generator
# ═══════════════════════════════════════════════════════════

def create_monogram(
    name: str,
    craft_type: str = "",
    size: int = 400,
    colors: tuple[tuple, tuple] | None = None,
) -> Image.Image:
    """Generate an artisan monogram logo from initials."""
    if colors is None:
        colors = (NAVY, GOLD)

    bg_color, text_color = colors
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle background
    margin = int(size * 0.05)
    draw.ellipse(
        [(margin, margin), (size - margin, size - margin)],
        fill=(*bg_color, 255),
    )

    # Inner ring
    ring_margin = int(size * 0.08)
    draw.ellipse(
        [(ring_margin, ring_margin), (size - ring_margin, size - ring_margin)],
        outline=(*text_color, 200),
        width=3,
    )

    # Initials
    initials = "".join(w[0].upper() for w in name.split() if w)[:2]
    init_font = font_bold(int(size * 0.35))
    bbox = draw.textbbox((0, 0), initials, font=init_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2, (size - th) / 2 - size * 0.05),
        initials,
        fill=(*text_color, 255),
        font=init_font,
    )

    # Craft label at bottom (inside circle)
    if craft_type:
        craft_font = font_regular(int(size * 0.07))
        craft_label = craft_type.upper()[:12]
        bbox2 = draw.textbbox((0, 0), craft_label, font=craft_font)
        cw = bbox2[2] - bbox2[0]
        draw.text(
            ((size - cw) / 2, size * 0.7),
            craft_label,
            fill=(*text_color, 180),
            font=craft_font,
        )

    return img


# ═══════════════════════════════════════════════════════════
# Brand Card (Printable Business Card)
# ═══════════════════════════════════════════════════════════

def create_brand_card(
    name: str,
    craft_type: str,
    district: str,
    state: str,
    tagline: str = "",
    upi_id: str = "",
    qr_data: str = "",
    colors: tuple[tuple, tuple] | None = None,
) -> Image.Image:
    """Generate a printable business card (3.5" x 2" at 300dpi = 1050x600)."""
    card_w, card_h = 1050, 600
    if colors is None:
        colors = (NAVY, GOLD)

    bg_color, accent = colors
    card = Image.new("RGB", (card_w, card_h), WHITE)
    draw = ImageDraw.Draw(card)

    # Left accent strip
    draw.rectangle([(0, 0), (8, card_h)], fill=bg_color)

    # Monogram
    mono = create_monogram(name, craft_type, size=140, colors=colors)
    card.paste(mono, (40, 40), mono)

    # Name
    name_font = font_bold(42)
    draw.text((200, 50), name, fill=bg_color, font=name_font)

    # Tagline / craft
    tag_font = font_regular(22)
    tag = tagline or f"{craft_type.title()} Artisan"
    draw.text((200, 105), tag, fill=TEAL, font=tag_font)

    # Location
    loc_font = font_regular(20)
    draw.text((200, 140), f"📍 {district}, {state}", fill=(*NAVY,), font=loc_font)

    # Divider
    draw.line([(40, 200), (card_w - 40, 200)], fill=LIGHT_GRAY, width=2)

    # UPI
    if upi_id:
        upi_font = font_regular(20)
        draw.text((40, 220), f"💰 UPI: {upi_id}", fill=NAVY, font=upi_font)

    # QR code on the right
    if qr_data:
        qr_img = create_qr_code(qr_data, size=200)
        card.paste(qr_img, (card_w - 240, 250), qr_img)

    # Bottom branding
    brand_font = font_bold(16)
    draw.text(
        (40, card_h - 40),
        "Powered by Viraasat.ai",
        fill=(*TEAL,),
        font=brand_font,
    )

    # Verified badge
    badge_font = font_semibold(16)
    draw.text(
        (40, card_h - 65),
        "✓ Verified Artisan",
        fill=(*GOLD,),
        font=badge_font,
    )

    return card


# ═══════════════════════════════════════════════════════════
# Auto Brand Colors (extract from product images)
# ═══════════════════════════════════════════════════════════

def extract_brand_colors(image: Image.Image, n_colors: int = 5) -> list[str]:
    """Extract dominant colors from a product image as hex strings."""
    # Resize small for speed
    small = image.copy().resize((100, 100), Image.LANCZOS).convert("RGB")
    colors = small.getcolors(maxcolors=10000)
    if not colors:
        return ["#122038", "#D4AF37", "#009688"]

    # Sort by frequency
    colors.sort(key=lambda c: c[0], reverse=True)

    # Filter out near-white / near-black
    result = []
    for count, (r, g, b) in colors:
        brightness = (r + g + b) / 3
        if 30 < brightness < 230:  # skip very dark/light
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            # Check it's distinct from already-picked colors
            if hex_color not in result:
                result.append(hex_color)
            if len(result) >= n_colors:
                break

    # Pad with brand defaults if needed
    defaults = ["#122038", "#D4AF37", "#009688", "#2C3E50", "#E67E22"]
    while len(result) < n_colors:
        result.append(defaults[len(result) % len(defaults)])

    return result


# ═══════════════════════════════════════════════════════════
# Compliance Checker
# ═══════════════════════════════════════════════════════════

def check_compliance(image: Image.Image) -> dict:
    """Verify image meets Amazon/Flipkart e-commerce specs."""
    w, h = image.size
    checks = {
        "min_1000px": w >= 1000 and h >= 1000,
        "square_aspect": abs(w - h) / max(w, h) < 0.05,
        "srgb_colorspace": image.mode in ("RGB", "RGBA"),
        "min_resolution": w >= 2000 and h >= 2000,
    }

    # Check if background is mostly white (sample corners)
    rgb = image.convert("RGB")
    corners = [
        rgb.getpixel((10, 10)),
        rgb.getpixel((w - 10, 10)),
        rgb.getpixel((10, h - 10)),
        rgb.getpixel((w - 10, h - 10)),
    ]
    white_corners = sum(1 for r, g, b in corners if r > 230 and g > 230 and b > 230)
    checks["white_background"] = white_corners >= 3

    issues = [k for k, v in checks.items() if not v]
    return {
        "platform_ready": len(issues) == 0,
        "checks": checks,
        "issues": issues,
    }


# ═══════════════════════════════════════════════════════════
# Apply All Overlays to Generated Cards
# ═══════════════════════════════════════════════════════════

def apply_overlays(
    cards: dict[str, Image.Image],
    parsed_data: dict,
    artisan_name: str = "",
    craft_type: str = "",
    region: str = "",
    qr_data: str = "",
    trust_score: float = 0.0,
) -> dict[str, Image.Image]:
    """
    Apply Pillow overlays to all 5 generated card images.
    Returns the final ready-to-save images.
    """
    result = {}

    # Card 1: Hero — clean, maybe QR if trust > 50%
    if "hero" in cards:
        hero = create_hero_card(cards["hero"])
        if trust_score > 50 and qr_data:
            hero = add_qr_overlay(hero, qr_data, position="bottom-right", qr_size=150)
        result["hero"] = hero

    # Card 2: Features — text overlay panel
    if "features" in cards:
        features_list = parsed_data.get("features", [])
        product_type = parsed_data.get("product_type", "")
        if product_type:
            # Use product type for title: "WATER BOTTLE FEATURES" or "SILK SHAWL FEATURES"
            short_type = product_type.split()[-1] if len(product_type.split()) > 2 else product_type
            title = f"{short_type.upper()} FEATURES"
        elif craft_type:
            title = f"{craft_type.upper()} FEATURES"
        else:
            title = "PREMIUM FEATURES"
        result["features"] = create_features_card(cards["features"], title, features_list)

    # Card 3: Heritage — clean image, no overlay
    if "heritage" in cards:
        result["heritage"] = cards["heritage"]

    # Card 4: Macro — clean image, no overlay
    if "macro" in cards:
        result["macro"] = cards["macro"]

    # Card 5: Lifestyle — clean image, no overlay
    if "lifestyle" in cards:
        result["lifestyle"] = cards["lifestyle"]

    return result
