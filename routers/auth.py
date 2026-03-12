"""Viraasat.ai — Auth Router

Endpoints: register (OTP), verify, profile CRUD.
"""

from __future__ import annotations

import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import (
    RegisterRequest, VerifyOTPRequest, OTPResponse,
    ArtisanCreate, ArtisanProfile, ArtisanUpdate,
    ProfileCompletion,
)
from services.profile_service import (
    create_profile, get_profile, get_profile_by_phone,
    update_profile, get_profile_completion, generate_monogram,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


# ═══════════════════════════════════════════════════════════
# OTP Registration (Firebase Phone Auth wrapper)
# ═══════════════════════════════════════════════════════════

@router.post("/register", response_model=OTPResponse)
async def register(req: RegisterRequest):
    """
    Send OTP to phone number.
    In production, this triggers Firebase Phone Auth.
    For hackathon demo, we skip actual OTP and auto-verify.
    """
    # Check if phone already registered
    existing = await get_profile_by_phone(req.phone)
    if existing:
        return OTPResponse(
            message="Welcome back! OTP sent.",
            phone=req.phone,
        )

    # In production: trigger Firebase Auth OTP here
    # firebase_admin.auth.create_session(...)
    return OTPResponse(
        message="OTP sent to your phone.",
        phone=req.phone,
    )


@router.post("/verify")
async def verify_otp(req: VerifyOTPRequest):
    """
    Verify OTP and return profile if exists.
    For hackathon: accepts any OTP and creates/loads profile.
    """
    # In production: verify with Firebase
    # firebase_admin.auth.verify_id_token(req.otp)

    existing = await get_profile_by_phone(req.phone)
    if existing:
        completion = get_profile_completion(existing)
        return {
            "status": "existing_user",
            "profile": existing.model_dump(),
            "completion": completion.model_dump(),
        }

    return {
        "status": "new_user",
        "message": "Phone verified. Please complete your profile.",
        "phone": req.phone,
    }


# ═══════════════════════════════════════════════════════════
# Profile CRUD
# ═══════════════════════════════════════════════════════════

@router.post("/profile", response_model=ArtisanProfile)
async def create_artisan_profile(data: ArtisanCreate):
    """Create a new artisan profile (called after onboarding flow)."""
    existing = await get_profile_by_phone(data.phone)
    if existing:
        raise HTTPException(409, "Artisan with this phone already exists")

    profile = await create_profile(data)
    return profile


@router.get("/profile/{artisan_id}", response_model=ArtisanProfile)
async def get_artisan_profile(artisan_id: str):
    """Get artisan profile by ID."""
    profile = await get_profile(artisan_id)
    if not profile:
        raise HTTPException(404, "Artisan not found")
    return profile


@router.put("/profile/{artisan_id}", response_model=ArtisanProfile)
async def update_artisan_profile(artisan_id: str, data: ArtisanUpdate):
    """Update artisan profile fields."""
    existing = await get_profile(artisan_id)
    if not existing:
        raise HTTPException(404, "Artisan not found")

    return await update_profile(artisan_id, data)


@router.get("/profile/{artisan_id}/completion", response_model=ProfileCompletion)
async def profile_completion(artisan_id: str):
    """Get profile completion percentage and nudges."""
    profile = await get_profile(artisan_id)
    if not profile:
        raise HTTPException(404, "Artisan not found")
    return get_profile_completion(profile)


@router.get("/profile/{artisan_id}/monogram")
async def get_monogram(artisan_id: str):
    """Get the artisan's monogram as PNG image."""
    try:
        mono = await generate_monogram(artisan_id)
    except ValueError:
        raise HTTPException(404, "Artisan not found")

    buf = BytesIO()
    mono.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
