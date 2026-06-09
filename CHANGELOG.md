# CHANGELOG

## [1.0.0] - 2026-06-09

### Added — Phase 0: Research & Environment Setup
- Full project scaffold: backend/ (Python), ui/ (Electron+React), extension/ (Chrome MV3)
- Python virtual environment with pyproject.toml dependency management
- AES-256-GCM encrypted SQLite database with PBKDF2 key derivation
- Configuration system via pydantic-settings with .env support

### Added — Phase 1: MVP Core Try-On Loop
- DensePose body scanning pipeline with Mediapipe Pose fallback
- Body measurement extraction from UV maps (height, chest, waist, hip, inseam, shoulder)
- Manual measurement input form as fallback
- 3D avatar mesh generation from UV coordinate grid (.obj)
- Webcam capture module (OpenCV) with React UI
- Wardrobe photo upload with background segmentation (SAM + GrabCut)
- BLIP-2 garment attribute extraction with VQA + confidence scoring
- FashionCLIP 512-dim embedding generation for similarity search
- OOTDiffusion virtual try-on with composite overlay fallback
- Garment image segmentation (SAM + GrabCut fallback)
- FastAPI server with 30+ REST endpoints + WebSocket
- Browser extension with product page detection (Shopee, Lazada, Zara, H&M, ASOS)

### Added — Phase 2: ML/AI Smart Features
- Size matching engine with ease allowances and brand corrections
- Size chart extraction (Donut OCR + HTML regex parser)
- Size history memory per brand
- Mix-match recommendation engine (FashionCLIP cosine + HSV color harmony + type compatibility)
- Complete-the-look feature for filling missing outfit slots
- Duplicate detection via FashionCLIP similarity threshold (0.92)
- Wardrobe analytics dashboard (type/color/season counts, cost-per-wear, duplicate groups)
- Model caching for loaded ML models
- Image preprocessing pipeline (resize, normalize)
- Result caching with TTL expiration in SQLite
- Batch wardrobe cataloging

### Added — Phase 3: External LLM API Integration
- ClaudeAdvisor with anthropic SDK and prompt caching
- GPT4VAdvisor with openai SDK
- OllamaAdvisor for offline operation (phi3:mini)
- Pluggable LLM fallback chain (Claude → GPT-4V → Ollama)
- BLIP-2 confidence threshold for automatic GPT-4V escalation
- Conversation history management (per-session SQLite storage)
- Wardrobe context summarizer for LLM prompts
- Occasion-based outfit generator
- Styling narrative generation for try-on results
- React chat UI with quick prompts and occasion selector

### Added — Phase 4: Self-Improving Knowledge Loop
- ArXiv crawler (cs.CV, cs.LG queries)
- HuggingFace model crawler (virtual-try-on, fashion tags)
- Papers with Code crawler (virtual-try-on, pose-estimation)
- Knowledge entry deduplication (title+source UNIQUE constraint)
- APScheduler for weekly automated crawl
- SECOND-KNOWLEDGE-BRAIN.md auto-update from crawl results
- Post-purchase size outcome tracking
- Style preference learning from outfit feedback
- Brand size calibration from purchase history
- Monthly wardrobe insight reports (underused items, style drift, cost-per-wear)

### Added — Phase 5: Testing, Polish & Deployment
- Error states and helpful messages throughout UI
- Settings panel (API keys, privacy, data wipe)
- Data protection: one-click full wipe (`DELETE /data/all`)
- electron-builder config for Windows + macOS packaging
- Browser extension ready for Chrome Web Store (Manifest V3)
- Health check endpoint for first-run validation
- Makefile + setup.sh + setup.bat for one-command setup
- CI pipeline (GitHub Actions): ruff lint + Python syntax check + UI build
- MIT License + CONTRIBUTING.md
- Comprehensive README with API documentation table

### Dependencies
- Core (required): torch, transformers, diffusers, fastapi, Pillow, opencv, pydantic, cryptography, anthropic, openai
- Optional (ml-heavy): detectron2, mediapipe, segment-anything, scikit-learn
- All ML models lazy-load with graceful fallbacks when unavailable
