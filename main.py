"""Viraasat.ai — FastAPI Application

One-Tap Digital Agency for rural artisans.
Zero digital literacy required. Professional e-commerce output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import HOST, PORT, ALLOWED_ORIGINS, OUTPUT_DIR, STATIC_DIR

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("viraasat")

# ── App ──
app = FastAPI(
    title="Viraasat.ai API",
    description=(
        "AI-powered digital agency for Indian artisans. "
        "Transforms product photos + voice into professional e-commerce listings."
    ),
    version="1.0.0",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Ensure directories exist ──
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ── Static files ──
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# ── Routers ──
from routers.auth import router as auth_router
from routers.products import router as products_router
from routers.sharing import router as sharing_router

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(sharing_router)


# ── Root — serve frontend ──
@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {
        "name": "Viraasat.ai",
        "tagline": "One-Tap Digital Agency for India's Artisans",
        "version": "1.0.0",
    }


# ── Health Check ──
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── Startup ──
@app.on_event("startup")
async def startup():
    logger.info("🏺 Viraasat.ai backend starting...")
    logger.info(f"   Output directory: {OUTPUT_DIR}")
    logger.info(f"   Static directory: {STATIC_DIR}")


# ── Run with uvicorn ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
