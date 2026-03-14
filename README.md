<div align="center">

# 🪔 Karu.ai (Viraasat.ai)

**The One-Tap Digital Agency for India’s Artisans.**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini%202.5%20Flash-8E75B2?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-F2DD6E?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)

*Zero digital literacy required. Professional e-commerce output.*

</div>

---

## 🌟 Overview
**Karu.ai (formerly Viraasat.ai)** bridges the gap between traditional Indian craftsmanship and modern e-commerce. By combining state-of-the-art visual AI with native voice-to-text processing, it empowers rural artisans to generate professional, platform-ready product listings, studio-quality images, and social media distributions using nothing more than a smartphone photo and a spoken description in Hindi or English.

---

## ✨ Key Features

### 📸 1. AI Product Studio
- **One-Tap Background Removal & Scene Generation:** Uses Google Gemini 2.5 Flash and robust bounding box detection to separate the handcrafted product from cluttered backgrounds.
- **Context-Aware Studio Environments:** Dynamically suggests and renders "Lifestyle" and "Heritage" backgrounds tailored specifically to the craft (e.g., *a traditional loom workshop for silk*).

### 🎙️ 2. Voice-to-Listing Intelligence
- **Native Language Parsing:** Artisans can dictate product details, price expectations, and heritage stories in Hindi, Hinglish, or English.
- **Automated Copywriting:** The AI pipeline automatically extracts materials, time spent, and pricing, generating:
  - Bulleted Amazon/Flipkart listings
  - Emoji-rich Instagram captions
  - Bilingual WhatsApp shareable links
  - High-traffic SEO keywords

### 💳 3. Digital Artisan Identity
- **Smart Onboarding:** Mobile-number + OTP login that dynamically tracks profile completion.
- **Brand Cards:** Generates downloadable, beautifully branded "Digital Identity Cards" (using Python `Pillow`) showing the artisan's name, craft, location, and a QR code.

### 📈 4. Pricing & Trust Engine
- **Fair Price Advisor:** Analyzes visual complexity, materials extracted from voice, and market trends to recommend minimum, maximum, and optimal retail prices.
- **Traceability & Provenance:** Generates a cryptographic "Provenance Hash" and measures AI processing time, creating a verifiable layer of authenticity for handcrafted goods.

### 🌍 5. Global Distribution
- **Headless Translation:** Integrated single-click Hindi ↔ English global translation using a customized, strictly-styled headless Google Translate implementation without breaking UI immersion.
- **One-Click Share Portals:** Deep-linked buttons to instantly bridge generated assets directly to Facebook Marketplace, Pinterest, Instagram, and WhatsApp.

---

## 🧠 Backend Architecture & Logic

Karu.ai is built on a high-performance **FastAPI** backend designed for modularity and speed.

- **`main.py`**: The central ASGI application. Orchestrates CORS, static file mounting, and includes sub-routers.
- **`services/ai_pipeline.py`**: The core "Brain". Uses a *combined* Gemini 2.5 Flash prompt strategy to simultaneously analyze the image, transcribe the audio, extract pricing, write SEO copy, and determine the optimal studio background in a single, lightning-fast API call.
- **`services/image_generator.py`**: Handles background removal, lighting harmonization, and rendering the product in new, AI-generated environments.
- **`services/pillow_engine.py` / `trust_engine.py`**: Uses Python Image Library (`Pillow`) for fast, server-side dynamic image composition. Generates the branded "Artisan Identity Cards" with real-time text wrapping, custom fonts, and profile pictures.
- **`routers/`**:
  - `auth.py`: Handles OTP generation, session storage, and profile completion calculations.
  - `products.py`: Manages the image upload, voice blob processing, AI generation pipeline, and database logging.
  - `sharing.py`: Manages the endpoints that generate dynamic distribution content (Facebook captions, Pinterest boards, WhatsApp texts) and serves the `brand-card` images directly as `image/png`.

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.10+
- A Google Gemini API Key
- (Optional) Supabase URL and Key for database persistence. *If omitted, the app defaults to an in-memory database.*

### 1. Clone the Repository
```bash
git clone https://github.com/nishant-kumar-yadav/Karu.ai.git
cd Karu.ai
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and insert your API keys:
```env
GEMINI_API_KEY="your_google_gemini_key_here"
# SUPABASE_URL="your_supabase_url" (Optional)
# SUPABASE_KEY="your_supabase_key" (Optional)
```

### 5. Run the Application
Start the FastAPI server using Uvicorn:
```bash
uvicorn main:app --reload
```

### 6. Access the Platform
Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

<div align="center">
  <i>Built to bring rural artistry to the global digital economy.</i><br>
  <b>Proudly crafted for India.</b>
</div>
