# wardrobe-twin-agent

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)

> **Your AI-powered virtual fitting room and smart wardrobe manager**

wardrobe-twin-agent creates a personalized 3D digital twin of your body from camera scans, catalogs your wardrobe, and simulates how new clothing items will look and fit — before you buy. All data stays local and encrypted.

---

## ✨ Features

- **🧍 Body Scanning** — DensePose / Mediapipe Pose → body measurements → 3D avatar
- **👗 Virtual Try-On** — OOTDiffusion renders garments on your digital twin
- **👔 Wardrobe Catalog** — Photo → BLIP-2 description → FashionCLIP embedding → searchable DB
- **📏 Size Matching** — Your measurements vs. size charts → perfect size recommendation
- **🔗 Mix-Match** — AI finds compatible outfit combinations from your existing wardrobe
- **💡 Style Advisor** — Claude / GPT-4V / Ollama fallback chain for styling advice
- **🔒 Privacy First** — All body data AES-256-GCM encrypted locally, zero cloud upload
- **🧩 Browser Extension** — Detect clothing on Shopee, Lazada, Zara, H&M, ASOS → instant try-on

---

## 🚀 Quick Start

### One-command setup (Linux/macOS)
```bash
git clone https://github.com/your-org/wardrobe-twin-agent.git
cd wardrobe-twin-agent
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

### One-command setup (Windows)
```cmd
git clone https://github.com/your-org/wardrobe-twin-agent.git
cd wardrobe-twin-agent
scripts\setup.bat
```

### Manual setup

**1. Python backend**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows

# Core only (no heavy ML models):
pip install -e .

# Or with all ML dependencies:
pip install -e ".[ml-heavy]"
```

**2. UI (Electron + React)**
```bash
cd ui && npm install
```

**3. Browser extension**
1. Open Chrome → `chrome://extensions`
2. Enable Developer mode
3. Load unpacked → select `extension/` folder

**4. Start**
```bash
# Terminal 1: Backend
python -m backend.api.server

# Terminal 2: UI
cd ui && npm run dev
```

### API Keys (optional)
Edit `.env` to enable cloud LLM advisors:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```
Without API keys, the app uses local Ollama (Phi-3-mini) as fallback.

---

## 🏗 Architecture

```
wardrobe-twin-agent/
├── backend/                    # Python FastAPI backend
│   ├── api/server.py          # 30+ REST endpoints + WebSocket
│   ├── ml/                    # ML pipeline modules
│   │   ├── body_scan/         # DensePose + Mediapipe Pose
│   │   ├── garment_understanding/  # BLIP-2 + FashionCLIP + SAM
│   │   ├── tryon/             # OOTDiffusion virtual try-on
│   │   └── sizing/            # Donut OCR + Size matching
│   ├── advisors/              # Claude → GPT-4V → Ollama fallback
│   ├── core/                   # Business logic, catalog, mix-match
│   ├── crawlers/               # ArXiv, HuggingFace, PapersWithCode
│   └── db/                     # SQLite + AES-256 encryption
├── ui/                         # Electron + React + Vite + Tailwind
│   └── src/pages/              # 5 pages: Scan, Wardrobe, TryOn, Advisor, Settings
├── extension/                  # Chrome Manifest V3 browser extension
│   └── src/                     # Background, content script, popup
├── config/settings.py          # All configuration
├── data/                        # Local data (avatars, images, cache)
└── scripts/                     # Setup scripts
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scan` | Body scan from webcam or manual measurements |
| `GET` | `/profiles` | List body profiles |
| `POST` | `/catalog` | Add garment (base64 image) |
| `POST` | `/catalog/upload` | Upload garment photo |
| `POST` | `/catalog/batch` | Batch upload multiple garments |
| `GET` | `/wardrobe` | List wardrobe items (filterable) |
| `GET` | `/wardrobe/search/text` | Search by text (FashionCLIP zero-shot) |
| `GET` | `/wardrobe/analytics` | Wardrobe analytics dashboard |
| `PATCH` | `/wardrobe/{id}` | Update garment attributes |
| `DELETE` | `/wardrobe/{id}` | Delete garment |
| `POST` | `/tryon` | Virtual try-on |
| `POST` | `/size-match` | Size recommendation |
| `POST` | `/size-chart/extract` | Extract size chart from image/HTML |
| `POST` | `/mix-match` | Find compatible items |
| `POST` | `/mix-match/complete-the-look` | Fill missing outfit slots |
| `POST` | `/advisor` | LLM style advice |
| `POST` | `/advisor/occasion` | Occasion-based outfit suggestions |
| `POST` | `/segment` | Remove garment background (SAM/GrabCut) |
| `POST` | `/crawl` | Trigger knowledge base crawl |
| `GET` | `/report/{profile_id}` | Monthly wardrobe report |
| `WS` | `/ws` | WebSocket for browser extension |

---

## 🧪 Development

```bash
# Lint
make lint

# Type check
make typecheck

# Run CI checks locally
pip install ruff mypy pytest pytest-asyncio
ruff check backend/ config/
mypy backend/ config/ --ignore-missing-imports
```

---

## 🔒 Privacy

| Data | Storage | Encryption |
|------|----------|-----------|
| Body scans | Local SQLite | AES-256-GCM |
| Wardrobe images | Local filesystem | AES-256-GCM (in DB) |
| Measurements | Local SQLite | AES-256-GCM |
| LLM API calls | Outbound only | Garment images sent, never body scans |
| Browser extension | localhost only | No external data transmission |

**One-click full data wipe:** `DELETE /data/all`

---

## 📦 Installation Options

```bash
# Lightweight (core API, no GPU models):
pip install -e .

# Full ML (includes detectron2, SAM, mediapipe):
pip install -e ".[ml-heavy]"

# GPU acceleration:
pip install -e ".[gpu]"
```

ML models are **lazy-loaded** — they download from HuggingFace on first use. The app works without them (using rule-based fallbacks), but features are enhanced with models.

---

## 📄 License

[MIT](LICENSE) — Free for personal and commercial use.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📚 Documentation

- [PROJECT-detail.md](PROJECT-detail.md) — Full technical specification
- [PROJECT-DEVELOPMENT-PHASE-TRACKING.md](PROJECT-DEVELOPMENT-PHASE-TRACKING.md) — Phase roadmap (all 6 phases complete ✅)
- [SECOND-KNOWLEDGE-BRAIN.md](SECOND-KNOWLEDGE-BRAIN.md) — Research knowledge base
