# PROJECT-detail.md — wardrobe-twin-agent
## Technical Specification & Source of Truth

---

## Executive Summary

**wardrobe-twin-agent** is an AI-powered desktop application and browser extension that creates a personalized 3D digital twin of a user's body, catalogs their existing wardrobe, and enables virtual try-on of new clothing items discovered on e-commerce platforms. When a user browses a clothing item online, the agent automatically simulates how it will look on their specific body, predicts fit accuracy using physical size-chart matching, and recommends mix-match combinations with clothes already in their wardrobe. The system operates locally to protect body scan privacy, with optional cloud LLM calls for advanced styling consultation.

---

## Problem Statement

### The Fashion E-Commerce Return Crisis
Online fashion is the highest-return retail category globally:
- **30–40% return rate** for clothing purchases online (vs. ~8% for in-store) — Statista, 2024
- **$816 billion** in merchandise returned in the US alone annually — NRF, 2023
- **70% of returns** cite incorrect size or fit as the primary reason — Narvar Consumer Report, 2023
- **58% of shoppers** have abandoned a clothing purchase due to uncertainty about fit — Shopify Research, 2023

### The Wardrobe Underutilization Problem
- Average person wears only **20% of their wardrobe** regularly — ThredUp Fashion Sustainability Report, 2023
- **$460 average** spent on clothes never worn or rarely worn per household per year
- Lack of outfit combination awareness causes duplicate purchases of similar items

### Root Causes
1. **No standardized sizing** — "Medium" differs by 2–4 cm across brands
2. **2D product images** don't convey drape, stretch, or fit on varied body shapes
3. **Wardrobe isolation** — shoppers can't easily visualize new items with existing clothes

---

## Target Users & Use Cases

### Primary Users
| Segment | Profile | Key Pain Point |
|---------|---------|---------------|
| Online fashion shoppers | Ages 18–45, shops 2–4× per month online | High return rate due to size uncertainty |
| Sustainable fashion advocates | Wants to "buy less, wear more" | Cannot maximize existing wardrobe value |
| Personal styling enthusiasts | Curates outfits actively | Needs outfit planning and mix-match tools |
| E-commerce platforms (B2B) | Fashion retailers, marketplaces | High logistics cost from returns |

### Use Cases
1. **Pre-purchase fit check:** User finds a jacket on Zara.com → extension triggers virtual try-on on their digital twin → size recommendation ("order M, your chest is 2cm wider than S chart")
2. **Wardrobe cataloging:** User photographs all clothes → agent extracts attributes (color, type, style) → searchable wardrobe database
3. **Outfit planning:** User asks "what can I wear with these jeans?" → agent suggests 3 compatible tops from existing wardrobe with virtual preview
4. **Duplicate detection:** User considers buying a navy blazer → agent flags 2 similar items already in wardrobe
5. **Style coaching:** User describes an occasion → Claude API generates a complete outfit suggestion from existing wardrobe

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WARDROBE-TWIN-AGENT SYSTEM                       │
├────────────────────┬────────────────────────────────────────────────┤
│   INPUT LAYER      │           PROCESSING CORE                      │
│                    │                                                │
│ ┌────────────────┐ │  ┌─────────────────────────────────────────┐  │
│ │ Camera/Webcam  │─┼─▶│  Body Scanning Pipeline                 │  │
│ │ Body Scan      │ │  │  DensePose → UV Map → 3D Mesh           │  │
│ └────────────────┘ │  │  → Measurement Extraction (cm matrix)   │  │
│                    │  └────────────────────┬────────────────────┘  │
│ ┌────────────────┐ │                       │                        │
│ │ Browser        │─┼─▶┌────────────────────▼────────────────────┐  │
│ │ Extension      │ │  │  Virtual Try-On Engine                  │  │
│ │ (Product page) │ │  │  OOTDiffusion + ControlNet              │  │
│ └────────────────┘ │  │  → Garment-on-Body Render               │  │
│                    │  └────────────────────┬────────────────────┘  │
│ ┌────────────────┐ │                       │                        │
│ │ Wardrobe       │─┼─▶┌────────────────────▼────────────────────┐  │
│ │ Photo Upload   │ │  │  Wardrobe Intelligence Engine           │  │
│ └────────────────┘ │  │  FashionCLIP + BLIP-2                   │  │
│                    │  │  → Embedding DB → Mix-Match Scorer      │  │
│                    │  └────────────────────┬────────────────────┘  │
├────────────────────┤                       │                        │
│   STORAGE LAYER    │  ┌────────────────────▼────────────────────┐  │
│                    │  │  Sizing Intelligence Engine             │  │
│ SQLite (local)     │  │  Donut OCR → Size Chart Parser          │  │
│ AES-256 encrypted  │  │  → Physical Measurement Matching        │  │
│ ┌──────────────┐   │  └────────────────────┬────────────────────┘  │
│ │ Body Profile │   │                       │                        │
│ │ Wardrobe DB  │   │  ┌────────────────────▼────────────────────┐  │
│ │ Size History │   │  │  LLM Advisor Layer (Pluggable)          │  │
│ │ Outfit Logs  │   │  │  Ollama (local) → Claude API → GPT-4V  │  │
│ └──────────────┘   │  └────────────────────┬────────────────────┘  │
├────────────────────┤                       │                        │
│   OUTPUT LAYER     │  ┌────────────────────▼────────────────────┐  │
│                    │  │  Electron UI / REST API                 │  │
│ Virtual try-on     │  │  → Virtual try-on preview               │  │
│ Size recommendation│  │  → Size recommendation card             │  │
│ Mix-match outfits  │  │  → Mix-match outfit gallery             │  │
│ Styling narrative  │  │  → AI styling narrative                 │  │
└────────────────────┴──┴─────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Source |
|-----------|-----------|--------|
| Primary language | Python 3.11 | python.org |
| Desktop UI | Electron 28 + React 18 | npmjs.com |
| Browser extension | Chrome Manifest V3 (JS) | developer.chrome.com |
| Body estimation | DensePose (detectron2) | Facebook Research |
| Virtual try-on | OOTDiffusion | HuggingFace |
| Pose control | ControlNet | HuggingFace |
| Garment embedding | FashionCLIP | HuggingFace |
| Garment description | BLIP-2 | Salesforce / HF |
| Size chart OCR | Donut | CLOVA AI / HF |
| Local LLM | Phi-3-mini (Ollama) | Microsoft / Meta |
| Cloud LLM (primary) | Claude claude-opus-4-8 | Anthropic API |
| Cloud LLM (secondary) | GPT-4o | OpenAI API |
| Local database | SQLite 3.45 | sqlite.org |
| Encryption | AES-256 (cryptography lib) | pyca/cryptography |
| Image processing | OpenCV 4.9, Pillow 10 | pypi.org |
| ML framework | PyTorch 2.2, Transformers 4.40 | pytorch.org / HF |
| Diffusion inference | diffusers 0.27 | HuggingFace |
| API server | FastAPI 0.111 | fastapi.tiangolo.com |
| IPC (extension ↔ app) | WebSocket (localhost:7331) | — |
| Dependency management | uv (fast pip alternative) | astral.sh/uv |

---

## ML/DL Models

### Body Estimation
| Model | ID | Purpose | Fine-tune needed |
|-------|-----|---------|-----------------|
| DensePose RCNN | `facebook/densepose_rcnn_R_101_FPN_s1x` | 2D→UV surface map of human body | No — pretrained on COCO-DensePose |
| OpenPose / ViTPose | `ViTPose-B` | Joint keypoint extraction for pose conditioning | No |

### Virtual Try-On
| Model | ID | Purpose | Fine-tune needed |
|-------|-----|---------|-----------------|
| OOTDiffusion | `levihsu/OOTDiffusion` | Diffusion-based garment-on-body rendering | No (use as-is) |
| HR-VITON | `sangyun-han/HR-VITON` | Fallback VTON for complex garments | No |
| ControlNet | `lllyasviel/ControlNet-v1-1` | Pose-guided generation conditioning | No |

### Garment Understanding
| Model | ID | Purpose | Fine-tune needed |
|-------|-----|---------|-----------------|
| FashionCLIP | `patrickjohncyh/fashion-clip` | Garment embedding, compatibility scoring | No |
| BLIP-2 | `Salesforce/blip2-opt-2.7b` | Garment attribute extraction (color, type, style) | No |
| Donut | `naver-clova-ix/donut-base` | Size chart OCR from product pages | Fine-tune on size chart dataset recommended |

### Fine-Tuning Plan
- **Donut for size charts:** Collect 500–1000 size chart images from major fashion retailers → fine-tune Donut for structured table extraction → host locally
- **FashionCLIP outfit compatibility:** If default cosine similarity proves insufficient, collect outfit rating dataset (Polyvore Outfits dataset) → contrastive fine-tune

### Training Data Sources
- [DeepFashion2](https://github.com/switchablenorms/DeepFashion2) — garment detection and segmentation
- [VITON-HD Dataset](https://github.com/shadow2496/VITON-HD) — paired garment/model images for try-on
- [Polyvore Outfits Dataset](https://github.com/mvasil/fashion-compatibility) — outfit compatibility pairs

---

## External LLM API Integration

### Pluggable Backend Design
```python
class LLMAdvisor:
    """Styling advisor with graceful fallback chain."""
    def __init__(self, config: dict):
        self.chain = [
            ClaudeAdvisor(config["ANTHROPIC_API_KEY"]),  # Primary
            GPT4VAdvisor(config["OPENAI_API_KEY"]),       # Secondary
            OllamaAdvisor(config["OLLAMA_HOST"]),         # Local fallback
        ]

    async def advise(self, prompt: str, images: list[bytes]) -> str:
        for advisor in self.chain:
            try:
                return await advisor.call(prompt, images)
            except (APIError, TimeoutError):
                continue
        return "Styling advisor unavailable. Please check your internet connection."
```

### Claude API Configuration
- **Model:** `claude-opus-4-8`
- **Use cases:** Outfit narrative generation, occasion-based styling consultation, trend analysis
- **Prompt caching:** System prompt with user body profile and wardrobe summary cached (saves 60–80% tokens)
- **Vision input:** Pass garment images as base64 for visual analysis

### GPT-4o Configuration
- **Use cases:** Complex garment attribute extraction when BLIP-2 is uncertain
- **Vision input:** Product images from e-commerce pages

### Local Ollama (Phi-3-mini)
- **Use cases:** Offline mode — all styling advice, wardrobe Q&A, size guidance
- **Deployment:** `ollama run phi3:mini` on localhost:11434

---

## Feature Specification

### MVP Features (Phase 1–2)
- [x] Body scanning via webcam using DensePose
- [x] Manual measurement input fallback (height, weight, chest, waist, hip)
- [x] Wardrobe photo cataloging with auto-tagging (color, type, style)
- [x] Virtual try-on simulation via OOTDiffusion
- [x] Size recommendation from size chart matching
- [x] Browser extension for product page detection (Shopee, Lazada, Zara, H&M, ASOS)
- [x] Mix-match suggestions from existing wardrobe
- [x] Basic wardrobe search ("show me all blue tops")

### Advanced Features (Phase 3–5)
- [ ] Outfit calendar — plan outfits for upcoming week
- [ ] Duplicate/similar item detection before purchase
- [ ] Style persona learning — system learns user's aesthetic preferences over time
- [ ] Occasion-based outfit generator ("dinner date", "job interview", "beach")
- [ ] Trend alignment scoring — how well a new item matches current micro-trends
- [ ] Multi-body-type simulation — preview items on different poses/stances
- [ ] Social sharing — export try-on previews as shareable cards (privacy: no body mesh included)
- [ ] Integration with Google Calendar for event-based outfit suggestions
- [ ] Resale value tracker — estimate secondhand value of wardrobe items
- [ ] Carbon footprint tracker — CO2 saved by not returning items, reusing existing wardrobe

---

## Full E2E Data Flow

### Flow 1: Initial Body Scan Setup
```
1. User opens app → prompted to stand in front of webcam
2. DensePose RCNN processes camera frame → generates UV body surface map
3. Measurement extraction algorithm converts UV map → physical cm measurements
   (chest, waist, hip, inseam, shoulder width, height estimate)
4. User reviews and corrects measurements manually if needed
5. Body profile stored locally in SQLite (AES-256 encrypted)
6. 3D avatar mesh generated and stored as .obj file (local only)
```

### Flow 2: Wardrobe Cataloging
```
1. User uploads clothing photos (or captures via webcam)
2. BLIP-2 extracts: item type, color, pattern, material estimate, style descriptors
3. FashionCLIP generates 512-dim embedding for compatibility matching
4. Item stored in wardrobe SQLite table: {id, image_blob, description, embedding, tags}
5. User can manually edit any auto-generated attribute
6. Wardrobe summary generated for LLM context (type counts, color palette distribution)
```

### Flow 3: New Item Try-On (Browser Extension Triggered)
```
1. User browses product page (e.g., Zara jacket)
2. Browser extension detects clothing product page → extracts:
   - Product images (front/back/detail)
   - Size chart (if present on page)
   - Garment metadata (brand, category, price)
3. Extension sends payload to local agent API (ws://localhost:7331)
4. Agent pipeline:
   a. Donut OCR → parse size chart into structured measurement table
   b. Size matching: user measurements vs. garment size chart → recommend size + fit notes
   c. BLIP-2 → extract garment attributes from product image
   d. OOTDiffusion → render garment on user's 3D body mesh → generate try-on image
5. FashionCLIP scores compatibility with top-5 items in existing wardrobe
6. LLM Advisor (Claude/GPT/Ollama) generates styling narrative:
   - Fit assessment ("This jacket will be slightly loose on your shoulders")
   - Mix-match combinations ("Pair with your navy chinos for a smart-casual look")
   - Purchase recommendation
7. Results displayed in extension popup + full UI panel
```

### Flow 4: Outfit Planning Request
```
1. User queries: "What to wear to a job interview tomorrow?"
2. LLM Advisor interprets occasion → identifies required style attributes
3. FashionCLIP searches wardrobe for high-compatibility item clusters
4. Agent assembles 3 complete outfit candidates from existing wardrobe
5. OOTDiffusion renders each outfit combination on user avatar
6. Claude API generates occasion-specific styling narrative for top recommendation
7. User can save outfit to calendar, mark worn, or reject
```

---

## Privacy & Security

| Concern | Approach |
|---------|---------|
| Body scan data | Stored locally only, AES-256 encrypted in SQLite, never transmitted without explicit opt-in |
| Wardrobe images | Local SQLite blob storage, AES-256, never sent to cloud |
| LLM API calls | Only garment images and abstract measurements sent (no body images to cloud) |
| Browser extension | Operates on localhost WebSocket only; no data sent to external servers by extension |
| Measurement transmission | Only anonymized measurements sent to Claude/GPT (not body images) |
| Data deletion | Single-click full data wipe — SQLite db drop + .obj file deletion |
| Key storage | AES key derived from user PIN + device hardware ID via PBKDF2 |

---

## Key Python/JS Dependencies

### Python Backend
```
torch==2.2.2
torchvision==0.17.2
transformers==4.40.0
diffusers==0.27.2
accelerate==0.30.0
detectron2==0.6
opencv-python==4.9.0.80
Pillow==10.3.0
fastapi==0.111.0
uvicorn==0.29.0
websockets==12.0
sqlcipher3==0.5.2       # AES-256 SQLite
cryptography==42.0.5
anthropic==0.28.0
openai==1.30.0
sentence-transformers==3.0.0
numpy==1.26.4
scipy==1.13.0
```

### Browser Extension (JS)
```json
{
  "dependencies": {
    "webextension-polyfill": "^0.10.0"
  },
  "devDependencies": {
    "webpack": "^5.91.0",
    "webpack-cli": "^5.1.4"
  }
}
```

### Electron UI
```json
{
  "dependencies": {
    "electron": "^28.3.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@tanstack/react-query": "^5.40.0",
    "tailwindcss": "^3.4.3",
    "zustand": "^4.5.2"
  }
}
```

---

## Improvement Suggestions

1. **Real-time webcam try-on** — Use lightweight VTON model (TryOnDiffusion-lite) for real-time AR overlay via webcam instead of batch rendering
2. **Multi-person household support** — Multiple body profiles per installation with PIN-separated vaults
3. **Brand size calibration memory** — Remember per-brand size quirks (e.g., "Zara runs small — always order one size up") from past purchase history
4. **Fabric physics simulation** — Add cloth simulation (TailorGAN or position-based dynamics) to show how stretchy/stiff fabrics behave during movement
5. **Seasonal wardrobe rotation** — Automatically categorize clothes by season and suggest what to bring out/store based on weather forecast API
6. **Budget optimizer** — Given a styling goal and budget, recommend the single new purchase that maximizes outfit combinations with existing wardrobe
7. **Sustainability score** — Rate each purchase decision by estimated cost-per-wear and environmental impact
8. **Voice interface** — Integrate whisper.cpp for hands-free wardrobe queries ("What do I have that matches these pants?")
9. **E-commerce API partnerships** — Official integrations with Shopee/Lazada/ASOS APIs for richer product data (exact fabric composition, model height/measurements)
10. **Collaborative wardrobe** — Allow couples/roommates to optionally share wardrobe catalogs for outfit coordination without sharing body profiles
