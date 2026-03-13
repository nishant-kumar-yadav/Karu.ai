"""Viraasat.ai — Supabase Database Layer"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazy-init Supabase client."""
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase not configured — using in-memory fallback")
        return None
    from supabase import create_client
    _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ═══════════════════════════════════════════════════════════
# In-memory fallback (for local dev / demo without Supabase)
# ═══════════════════════════════════════════════════════════

_mem_artisans: dict[str, dict] = {}
_mem_products: dict[str, dict] = {}
_mem_scans: list[dict] = []


# ═══════════════════════════════════════════════════════════
# Artisan CRUD
# ═══════════════════════════════════════════════════════════

async def create_artisan(data: dict) -> dict:
    """Insert a new artisan record."""
    client = _get_client()
    if client:
        result = client.table("artisans").insert(data).execute()
        return result.data[0]
    # In-memory fallback
    _mem_artisans[data["id"]] = data
    return data


async def get_artisan(artisan_id: str) -> Optional[dict]:
    """Fetch artisan by ID."""
    client = _get_client()
    if client:
        result = client.table("artisans").select("*").eq("id", artisan_id).execute()
        return result.data[0] if result.data else None
    return _mem_artisans.get(artisan_id)


async def get_artisan_by_phone(phone: str) -> Optional[dict]:
    """Fetch artisan by phone number."""
    client = _get_client()
    if client:
        result = client.table("artisans").select("*").eq("phone", phone).execute()
        return result.data[0] if result.data else None
    for a in _mem_artisans.values():
        if a.get("phone") == phone:
            return a
    return None


async def update_artisan(artisan_id: str, data: dict) -> dict:
    """Update artisan fields."""
    data["updated_at"] = datetime.utcnow().isoformat()
    client = _get_client()
    if client:
        result = client.table("artisans").update(data).eq("id", artisan_id).execute()
        return result.data[0]
    if artisan_id in _mem_artisans:
        _mem_artisans[artisan_id].update(data)
        return _mem_artisans[artisan_id]
    return data


# ═══════════════════════════════════════════════════════════
# Product CRUD
# ═══════════════════════════════════════════════════════════

async def create_product(data: dict) -> dict:
    """Insert a new product record."""
    client = _get_client()
    if client:
        result = client.table("products").insert(data).execute()
        return result.data[0]
    _mem_products[data["id"]] = data
    return data


async def get_product(product_id: str) -> Optional[dict]:
    """Fetch product by ID."""
    client = _get_client()
    if client:
        result = client.table("products").select("*").eq("id", product_id).execute()
        return result.data[0] if result.data else None
    return _mem_products.get(product_id)


async def get_products_by_artisan(artisan_id: str) -> list[dict]:
    """Fetch all products for an artisan."""
    client = _get_client()
    if client:
        result = (
            client.table("products")
            .select("*")
            .eq("artisan_id", artisan_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    return [p for p in _mem_products.values() if p.get("artisan_id") == artisan_id]


# ═══════════════════════════════════════════════════════════
# QR Scan Analytics
# ═══════════════════════════════════════════════════════════

async def record_scan(data: dict) -> dict:
    """Record a QR scan event."""
    client = _get_client()
    if client:
        result = client.table("scans").insert(data).execute()
        return result.data[0]
    _mem_scans.append(data)
    return data


async def get_scan_stats(product_id: str) -> dict[str, Any]:
    """Get scan statistics for a product."""
    client = _get_client()
    if client:
        result = client.table("scans").select("*").eq("product_id", product_id).execute()
        scans = result.data
    else:
        scans = [s for s in _mem_scans if s.get("product_id") == product_id]

    total = len(scans)
    actions = {}
    for s in scans:
        act = s.get("action_taken", "viewed")
        actions[act] = actions.get(act, 0) + 1

    return {"total_scans": total, "actions": actions}


async def get_scans_for_artisan(artisan_id: str) -> list[dict]:
    """Get all scan events across all products for an artisan."""
    client = _get_client()
    if client:
        # Get artisan's products first, then their scans
        products = await get_products_by_artisan(artisan_id)
        product_ids = [p["id"] for p in products]
        if not product_ids:
            return []
        result = client.table("scans").select("*").in_("product_id", product_ids).execute()
        return result.data
    # In-memory fallback
    products = await get_products_by_artisan(artisan_id)
    product_ids = {p["id"] for p in products}
    return [s for s in _mem_scans if s.get("product_id") in product_ids]
