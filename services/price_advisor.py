"""Viraasat.ai — AI Price Advisor

Uses Gemini with search grounding to research market prices
for similar handcrafted products and suggest fair pricing.
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

PRICE_PROMPT = """You are an expert on Indian product marketplace pricing.

Product: {product_type}
Materials: {materials}
Crafting time: {crafting_time}
Region: {region}
Seller's asked price: {asked_price}
Product type: {is_handcrafted}

Research and provide fair market pricing. Consider:
1. Similar products on Amazon India, Flipkart, Meesho
2. Material costs and crafting/manufacturing time
3. If the seller specified an asked price, use it as a STRONG anchor — recommend within ±20% of it unless clearly unreasonable

PRICING RULES:
- For HANDCRAFTED products: Consider artisan wages, material costs, heritage value. Check GoCoop, iTokri, Okhai for comparable handcrafted items. Ensure artisan gets fair value.
- For MANUFACTURED/BRANDED products: Check Amazon India, Flipkart, JioMart for the EXACT brand and model. A Cello 1L water bottle is ₹200-350, NOT ₹2000+. A Milton bottle is ₹300-500. Match real retail MRP.
- NEVER inflate manufactured product prices to artisan levels.
- If asked_price is provided, respect it as the seller knows their product.

Return JSON:
{{
  "min_price": 0,
  "max_price": 0,
  "recommended_price": 0,
  "reasoning": "2-3 sentences explaining the price recommendation",
  "similar_products": ["list of 3-5 similar products with their prices found online"],
  "artisan_fair_wage": "estimated fair daily wage for this type of work (if handcrafted, else 'N/A')"
}}

Be specific with real price ranges in INR (₹)."""


async def get_price_advice(
    product_type: str,
    materials: list[str],
    crafting_time: str = "",
    region: str = "",
    asked_price: float = 0,
    is_handcrafted: bool = True,
) -> dict:
    """Get AI-powered price recommendation with market research."""
    prompt = PRICE_PROMPT.format(
        product_type=product_type,
        materials=", ".join(materials) if materials else "various materials",
        crafting_time=crafting_time or "not specified",
        region=region or "India",
        asked_price=f"₹{asked_price}" if asked_price else "not specified",
        is_handcrafted="HANDCRAFTED / artisan-made" if is_handcrafted else "MANUFACTURED / factory-made / branded",
    )

    # Use search grounding for real market data
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=FLASH_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception:
        # Fallback without search grounding if not available
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


# ═══════════════════════════════════════════════════════════
# Negotiation Coach
# ═══════════════════════════════════════════════════════════

NEGOTIATION_PROMPT = """You are a friendly negotiation coach for an Indian artisan. Speak in simple Hindi-English mix.

Artisan says: "{artisan_message}"
Product type: {product_type}
Fair market price range: ₹{price_min} - ₹{price_max}
Recommended price: ₹{recommended}

Give the artisan:
1. A confidence boost (acknowledge their craft's value)
2. A specific counter-offer amount to quote
3. A simple line they can say (in Hindi/Hinglish)
4. Why this price is justified

Return JSON:
{{
  "response": "Your full coaching response in Hindi-English mix",
  "suggested_counter": 0,
  "script_line": "A line the artisan can directly say to the buyer",
  "justification": "Why this price is fair - facts they can mention"
}}"""


async def negotiate(
    artisan_message: str,
    product_type: str,
    price_min: float,
    price_max: float,
    recommended: float,
) -> dict:
    """Provide negotiation coaching based on market data."""
    prompt = NEGOTIATION_PROMPT.format(
        artisan_message=artisan_message,
        product_type=product_type,
        price_min=price_min,
        price_max=price_max,
        recommended=recommended,
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

    return json.loads(raw)
