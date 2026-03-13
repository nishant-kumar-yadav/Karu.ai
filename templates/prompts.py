"""Viraasat.ai — Prompt Templates for Category-Specific Image Generation

3-Layer Architecture:
  Layer 1: Category templates with {placeholders}
  Layer 2: Gemini fills placeholders with product-specific details
  Layer 3: Constraint injection (always appended)
"""

# ── Layer 3: Universal Constraints (always appended) ──────

STUDIO_CONSTRAINT = """
Product-only studio photograph. Clean image, no text overlays or graphics. 
Preserve exact product colors, shape, and proportions from reference. 
Photorealistic, 8K resolution, professional commercial quality.
"""

CREATIVE_CONSTRAINT = """
Single continuous photograph, not a collage. Product colors and form preserved 
from reference. Photorealistic, professional quality. No text or graphics.
"""

NEGATIVE_PROMPT = (
    "text, words, letters, numbers, watermark, logo, label, annotation, "
    "blurry, low quality, cartoon, illustration, distorted"
)


# ── Layer 1: Category Templates ──────────────────────────

CATEGORY_TEMPLATES: dict[str, dict[str, str]] = {

    # ── TEXTILES ──────────────────────────────────────────
    "textiles": {
        "hero": (
            "Create a premium e-commerce hero photograph of {product_description}. "
            "Present the {material} product BEAUTIFULLY — fold it neatly, drape it elegantly, "
            "or arrange it in the most visually appealing way for a product listing. "
            "The product is {color_description} with {texture_description}. "
            "Seamless pure white studio background. Soft diffused lighting. "
            "Polished surface with subtle reflection. The product fills 60-70% of the frame. "
            "IMPORTANT: Keep the EXACT same color and material as the reference photo. "
            "Do NOT add any items or accessories not in the reference."
        ),
        "features": (
            "The same {product_description} displayed on a polished white surface "
            "with soft reflections. The fabric is partially unfolded to reveal "
            "the intricate {unique_details}. Shot from a three-quarter angle. "
            "Clean, bright studio lighting. Space on the right side for overlay graphics."
        ),
        "heritage": (
            "A lifestyle context shot: the {product_description} draped over a "
            "traditional wooden loom or handcraft workspace. Warm, golden-hour "
            "lighting. Bokeh background showing artisan tools. The {material} "
            "textile is the clear hero of the frame. Rustic yet premium feel."
        ),
        "macro": (
            "An extreme macro close-up of the {product_description}'s weave pattern. "
            "Sharp focus on individual {material} threads showing the {texture_description}. "
            "Visible interlocking weave structure. Studio lighting creating micro-shadows "
            "between threads. The {color_description} is vivid at this scale."
        ),
        "lifestyle": (
            "The {product_description} styled in a modern, minimalist living room. "
            "Draped over a designer chair or spread on a bed with neutral-toned decor. "
            "Natural window light streams in. The {color_description} of the textile "
            "pops against the contemporary interior. Aspirational lifestyle photography."
        ),
    },

    # ── POTTERY ───────────────────────────────────────────
    "pottery": {
        "hero": (
            "Create a premium e-commerce hero photograph of {product_description}. "
            "A beautifully styled {material} pottery piece on a polished white surface "
            "with subtle reflection. {color_description}. Present it at its most appealing angle. "
            "Soft studio lighting defines the curves and form. Pure white background. "
            "IMPORTANT: Keep the EXACT same color, glaze, and shape as the reference photo. "
            "Do NOT add any items or accessories not in the reference."
        ),
        "features": (
            "The {product_description} shown from a slightly elevated angle on a "
            "white surface. The {unique_details} are clearly visible. Soft directional "
            "lighting accentuates the glaze and form. Space on the right for graphics."
        ),
        "heritage": (
            "The {product_description} placed on a rustic wooden surface next to "
            "traditional pottery tools — a wheel, clay, wooden paddles. Warm ambient "
            "lighting. Artisan workshop atmosphere with bokeh background. The pottery "
            "piece is the sharp focal point."
        ),
        "macro": (
            "An extreme macro shot of the {product_description}'s surface. Sharp focus "
            "on the {material} glaze texture showing {texture_description}. Visible "
            "brush strokes or hand-finished details. Studio lighting revealing "
            "surface variations. {color_description} at microscopic detail."
        ),
        "lifestyle": (
            "The {product_description} styled in a modern kitchen or dining setting. "
            "Placed on a marble countertop or wooden shelf with minimalist decor. "
            "Fresh flowers or herbs nearby. Natural daylight. The {color_description} "
            "pottery complements the contemporary space."
        ),
    },

    # ── JEWELRY ───────────────────────────────────────────
    "jewelry": {
        "hero": (
            "Create a stunning e-commerce hero photograph of {product_description}. "
            "Display the {material} jewelry piece beautifully on a small velvet cushion "
            "or marble slab against a pure white background. {color_description}. "
            "Dramatic studio lighting creates sparkle and highlights the metalwork. "
            "IMPORTANT: Keep the EXACT same metal color, stones, and design as the reference. "
            "Do NOT add any items or accessories not in the reference."
        ),
        "features": (
            "The {product_description} laid flat on a clean white surface, showing "
            "its full design. {unique_details} clearly visible. Directional lighting "
            "creates controlled reflections on the {material}. Three-quarter overhead angle."
        ),
        "heritage": (
            "The {product_description} arranged on an antique fabric or ornate tray. "
            "Surrounded by traditional making tools — hammer, anvil, wire. Warm golden "
            "lighting evoking a craftsman's workshop. The jewelry is the sharp hero."
        ),
        "macro": (
            "An extreme macro shot of the {product_description} showing {texture_description}. "
            "Visible {material} grain, engravings, or stone settings. Pin-sharp focus. "
            "Studio lighting creating tiny highlights on every facet. {color_description}."
        ),
        "lifestyle": (
            "The {product_description} styled on a marble vanity or near a mirror. "
            "Soft natural light. Minimal props — a silk scarf, a perfume bottle. "
            "The jewelry catches light beautifully. Aspirational luxury feel."
        ),
    },

    # ── WOODWORK ──────────────────────────────────────────
    "woodwork": {
        "hero": (
            "Create a premium e-commerce hero photograph of {product_description}. "
            "The {material} woodwork piece presented at its most appealing angle "
            "on a polished white surface with subtle reflection. {color_description}. "
            "Soft studio lighting makes the wood grain and carving details crisp. "
            "Pure white background. "
            "IMPORTANT: Keep the EXACT same wood color, grain, and carving as the reference. "
            "Do NOT add any items or accessories not in the reference."
        ),
        "features": (
            "The {product_description} from a three-quarter elevated angle. "
            "{unique_details} — carved patterns, joinery, or inlay work clearly visible. "
            "Directional side-lighting accentuates the depth of carvings."
        ),
        "heritage": (
            "The {product_description} placed in a traditional woodworking workshop. "
            "Surrounded by chisels, hand planes, wood shavings. Warm golden lighting. "
            "The finished piece contrasts beautifully with raw wood around it."
        ),
        "macro": (
            "An extreme macro close-up of {product_description}'s woodwork detail. "
            "Sharp focus on {texture_description} — grain patterns, carved motifs, "
            "hand-polished finish. {color_description}. Studio side-lighting."
        ),
        "lifestyle": (
            "The {product_description} placed in a modern minimalist home — on a shelf, "
            "side table, or as a centerpiece. Clean interior with plants and books. "
            "Natural window light. The handcrafted piece adds warmth to the modern space."
        ),
    },

    # ── METALWORK ─────────────────────────────────────────
    "metalwork": {
        "hero": (
            "Create a premium e-commerce hero photograph of {product_description}. "
            "The {material} metalwork piece on a polished surface with dramatic reflection. "
            "{color_description}. Studio lighting creates controlled highlights on the metal. "
            "Pure white background. Present it at its most striking angle. "
            "IMPORTANT: Keep the EXACT same metal, patina, and design as the reference. "
            "Do NOT add any items or accessories not in the reference."
        ),
        "features": (
            "The {product_description} from an elevated angle showing craftsmanship. "
            "{unique_details} visible — engravings, patina, hammer marks. "
            "Directional lighting reveals surface texture."
        ),
        "heritage": (
            "The {product_description} in a traditional metalsmith's forge setting. "
            "Warm amber lighting, anvil and tools in soft focus behind. The polished "
            "piece gleams against the rustic backdrop."
        ),
        "macro": (
            "Extreme macro of {product_description}'s metal surface. {texture_description} "
            "at microscopic level — hammer texture, engravings, patina layers. "
            "{color_description}. Pin-sharp studio lighting."
        ),
        "lifestyle": (
            "The {product_description} displayed in a modern interior — on a console, "
            "bookshelf, or dining table. Warm ambient lighting. The metalwork adds "
            "artisanal character to the contemporary space."
        ),
    },

    # ── GENERIC (fallback for any category) ───────────────
    "generic": {
        "hero": (
            "Create a premium e-commerce hero photograph of {product_description}. "
            "Present the product BEAUTIFULLY — style it, arrange it, and display it "
            "in the most visually appealing way for a product listing. "
            "The product is {color_description} and made of {material}. "
            "Seamless PURE WHITE infinity-curve studio background. "
            "Two soft key lights at 45 degrees. Polished surface with subtle reflection. "
            "The product fills 60-70% of the frame. Front three-quarter perspective. "
            "IMPORTANT: Keep the EXACT same color, material, and texture as the reference photo. "
            "Do NOT add ANY items, accessories, packaging, or props not visible in the reference. "
            "ONLY the product itself, beautifully presented."
        ),
        "features": (
            "A product photograph of {product_description} positioned on the far LEFT EDGE of the frame. "
            "The product occupies ONLY the leftmost 35% of the image. "
            "The entire RIGHT 65% of the image is SOLID PURE WHITE (#FFFFFF) — completely blank, "
            "no shadows, no gradients, no reflections, no objects, no floor line. "
            "Think of it as: [product on left] [giant white rectangle on right]. "
            "Clean white background everywhere. Soft studio lighting. "
            "The white space on the right will be used for text overlay — it MUST be empty."
        ),
        "heritage": (
            "Editorial product photograph: place this {product_description} in "
            "{heritage_setting}. Product is the sharp focal point. Warm cinematic "
            "bokeh, golden-hour lighting. 50mm f/1.8 full-frame. Preserve product "
            "colors and form. Premium magazine-quality storytelling photograph."
        ),
        "macro": (
            "Extreme macro close-up of {product_description}, focusing tightly on "
            "{macro_focus_area}. Canon RF 100mm f/2.8L Macro, f/2.8. Fill the frame "
            "with this single detail. Studio side-lighting reveals texture depth. "
            "{color_description}. Creamy bokeh. Single continuous photograph."
        ),
        "lifestyle": (
            "Lifestyle product photograph of this {product_description} in "
            "{lifestyle_setting}. Product placed naturally as focal point. Soft natural "
            "daylight, 85mm f/1.4, shallow depth of field. Warm aspirational atmosphere. "
            "Minimal props. Product colors match reference. Editorial photograph."
        ),
    },
}

# Add aliases for remaining categories that map to generic
for _cat in ("leather", "paper", "paintings", "cane_bamboo"):
    if _cat not in CATEGORY_TEMPLATES:
        CATEGORY_TEMPLATES[_cat] = CATEGORY_TEMPLATES["generic"]


CARD_TYPES = ["hero", "features", "heritage", "macro", "lifestyle"]


def get_filled_prompt(category: str, card_type: str, values: dict[str, str]) -> str:
    """Fill a template with product-specific values and append constraints."""
    templates = CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["generic"])
    template = templates.get(card_type, templates["hero"])

    # Safe fill — missing keys become empty strings
    filled = template
    for key, val in values.items():
        filled = filled.replace(f"{{{key}}}", val)

    # Remove any unfilled placeholders
    import re
    filled = re.sub(r"\{[a-z_]+\}", "", filled)

    return filled.strip() + "\n" + (STUDIO_CONSTRAINT if card_type in ("hero", "features") else CREATIVE_CONSTRAINT)
