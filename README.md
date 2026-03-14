<div align="center">

<img src="static/favicon.svg" alt="Karu.ai Logo" width="120" />

# 🪔 Karu.ai


[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini%202.5%20Flash-8E75B2?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-F2DD6E?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Build Status](https://img.shields.io/badge/Status-Live%20Platform-success?style=for-the-badge)]()

*Zero digital literacy required. Professional e-commerce output in seconds.*

---

*"Karu.ai bridges the ultimate divide: transforming traditional Indian craftsmanship into platform-ready global e-commerce listings using the lowest-barrier interface possible—a simple smartphone camera and a voice note."*

</div>

---

## 🌟 The Problem We Are Solving

India has over 200 million artisans and micro-entrepreneurs producing incredibly high-quality, handcrafted goods—from Banarasi silk to Jaipur blue pottery. Yet, less than **2%** of these creators are able to successfully sell their products online.

**Why?**
The digital barrier to entry is immense. Creating a successful e-commerce business requires:
1. Professional studio photography and lighting
2. Fluent English copywriting and SEO keyword research
3. Graphic design skills for social media templates
4. Market research for pricing
5. Distribution knowledge across WhatsApp, Instagram, and Facebook

**Karu.ai completely eliminates this barrier.** 
By leveraging state-of-the-art Generative AI, we have condensed an entire digital marketing, photography, and copywriting agency into a **single, zero-friction interface.**

---

## 🔥 Magical User Experience (UX / Core Flow)

The genius of Karu.ai lies in its absolute simplicity. We designed this platform from the ground up for a user who may have never used a computer.

1. **Snap & Speak:** The artisan takes a raw, unedited photo of their product (even on a remarkably cluttered background). They hold a microphone button and speak naturally: *"Yeh haath se bani brass ki murti hai, mujhe iske 400 rupaiye chahiye."* (This is a handmade brass statue, I want 400 rupees for it).
2. **The "Wait, That's It?" Moment:** The artisan clicks "Generate."
3. **The Reveal:** Within 10 seconds, the AI pipeline:
   - Magnetically cuts out the product from the messy background.
   - Generates 4 stunning, studio-quality lifestyle environments perfectly suited to the craft.
   - Translates their Hindi voice note into professional, SEO-optimized English Amazon bullet points.
   - Creates emoji-rich Instagram captions with viral hashtags.
   - Advises on minimum, maximum, and fair market prices.
4. **One-Click Distribution:** The artisan taps the WhatsApp, Facebook, or Pinterest button to instantly push their newly branded product to their audience. 

---

## ✨ Unfair Advantages & Key Features

### 📸 1. Dynamic AI Product Studio
- **Precision Auto-Cropping:** Uses Gemini 2.5 Vision to accurately draw a bounding box around the core product and uses smart background removal to extract it.
- **Context-Aware Scene Generation:** Rather than pasting the product into generic backgrounds, the AI determines the exact *type* of product and generates highly specific "Lifestyle" (e.g., *a marble vanity for jewelry*) and "Heritage" (e.g., *a silk traditional handloom*) staging.
- **Harmonized Lighting & Shadows:** The generated images don't look like cheap Photoshop cutouts. The AI processes natural drop shadows and edge lighting.

### 🎙️ 2. Multilingual Voice-to-Listing Intelligence
- **Native Language Parsing:** The pipeline natively understands rural Hindi, Hinglish, and English dialects.
- **Automated Copywriting:** Extracts meaning (materials used, time spent, asked price) and generates:
  - Bulleted Amazon/Flipkart listings
  - Emoji-rich Instagram captions
  - Bilingual WhatsApp shareable links
  - High-traffic SEO keywords tailored to the current platform algorithms.

### 💳 3. The Digital Artisan Identity & Brand Kit
- **Instant Brand Equity:** Artisans get their own "Digital Identity Card."
- **Server-Side Rendering (`Pillow` Engine):** We dynamically assemble beautiful, downloadable PNG identity cards on the backend, complete with the artisan's name, craft, location, generated QR codes, and performance stats.

### 📈 4. Pricing Advisor & Trust Engine
- **Fair Market Estimations:** Analyzes the visual complexity of the image and the materials mentioned in the voice note to recommend the optimum retail price against the artisan's natively requested price.
- **Traceability (Provenance):** Emits a cryptographic "Provenance Hash" measuring AI processing elements to establish a layer of unforgeable authenticity for handcrafted goods.

### 🌍 5. Global Reach & Headless Localization
- **Headless Translation System:** We built a custom Google Translate integration that hides traditional clunky UI banners/tooltips and attaches directly to a clean, single-click toggle in our nav-bar (`EN` ↔ `हिंदी`), localizing the entire platform instantly without breaking immersion.
- **Frictionless Social Hub:** Pre-filled deep links into the Facebook Marketplace Creator, Pinterest Pin Builder, and WA API.

---

## 🧠 Technical Architecture & Backend Brilliance

Karu.ai is built on a **Modular FastAPI** backend designed for parallel execution, high concurrency, and lightning speed.

### The "One-Shot" Gemini Pipeline Strategy
In typical LLM implementations, developers make multiple round-trip API calls (one for vision, one for text parsing, one for SEO formatting). **We engineered a single, highly-complex, aggressively typed Gemini 2.5 Flash pipeline call (`ai_pipeline.py`).**

In milliseconds, this single unified prompt:
1. Absorbs the image bytes.
2. Cross-references it with the voice transcript.
3. Automatically translates the vernacular.
4. Spits out tightly structured JSON containing Pricing, 3 distinct Copywriting formats, Background Prompts, SEO tags, and Materials in one network request—**maximizing efficiency and minimizing latency.**

### The Tech Stack
* **Frontend:** Vanilla JavaScript & Clean CSS (Flexbox/Grid). We explicitly avoided heavy frameworks (React/Next) to ensure the platform loads instantly on 3G mobile networks in rural India. Hardware-accelerated CSS animations make the UI feel ultra-premium.
* **Backend:** FastAPI (Python 3.10+ ASGI framework).
* **Intelligence:** Google Gemini 2.5 Flash API.
* **Image Compositing:** Python `Pillow` (PIL) for generating dynamic, text-wrapped, grid-aligned digital identity cards and asset packages in memory using `BytesIO` streams (no disk I/O bottlenecks).
* **Security & Auth:** Extensible session-based OTP auth flows cleanly partitioned in `auth.py`.

---

## 🚀 How to Run Locally

Want to experience the magic yourself? Setting up Karu.ai takes less than 2 minutes.

### Prerequisites
- Python 3.10+
- A [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### 1. Clone & Entwine
```bash
git clone https://github.com/nishant-kumar-yadav/Karu.ai.git
cd Karu.ai
```

### 2. Sandbox Setup (Virtual Environment)
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

### 4. Inject Keys
Copy our example template to your core `.env` environment file:
```bash
cp .env.example .env
```
Open `.env` in any text editor and insert your Gemini payload:
```env
GEMINI_API_KEY="your_google_gemini_key_here"
```

### 5. Ignite the Server
Start the high-performance Uvicorn ASGI server:
```bash
uvicorn main:app --reload
```

### 6. Marvel
Open your browser and navigate to the local portal:
**➡️ [http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

<div align="center">

*Engineered to redefine parity.*<br>
**Empowering the next generation of India's digital economy.**

<br>

![Karu.ai Dashboard Preview](https://via.placeholder.com/800x400/1e1e1e/d4af37?text=The+One-Tap+Agency)

</div>
