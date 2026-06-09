# CLAUDE.md â€” wardrobe-twin-agent

## Project Identity
- **Name:** wardrobe-twin-agent
- **Tagline:** Your AI-powered virtual fitting room and smart wardrobe manager
- **Status:** Phase 0 â€” Research & Environment Setup
- **Current Phase:** 0 of 5

## Core Problem
Online clothing shoppers face a persistent challenge: items purchased online frequently don't fit correctly or match personal style, leading to return rates of 30â€“40% for fashion e-commerce â€” the highest return category globally. The wardrobe-twin-agent solves this by creating a personalized 3D digital twin of the user's body from camera scans, cataloging their existing wardrobe, and automatically simulating how new clothing items will look and fit â€” including mix-match suggestions with existing clothes â€” before purchase. This reduces buyer uncertainty, cuts return rates, and helps users maximize value from clothes they already own.

## Architecture Summary
- **Platform:** Desktop application (Python backend + Electron UI) + browser extension for e-commerce integration
- **ML Stack:** Virtual Try-On (VTON) diffusion models, 3D body pose/surface estimation (DensePose), outfit compatibility classification (FashionCLIP), garment attribute extraction (BLIP-2)
- **Local SLM:** Phi-3-mini (via Ollama) for offline styling advice and wardrobe Q&A
- **Optional External APIs:** Claude API for advanced styling narrative, GPT-4V for complex garment analysis

## Key Technical Decisions
1. Use Facebook DensePose for 2D camera image â†’ 3D body surface mesh reconstruction
2. Use OOTDiffusion (levihsu/OOTDiffusion) as primary virtual try-on pipeline â€” diffusion-based for realistic fabric drape
3. Store wardrobe catalog locally in SQLite with AES-256 encrypted image blobs and FashionCLIP embeddings
4. Browser extension intercepts product page images/metadata from major e-commerce sites and sends to local agent via localhost API
5. Size matching uses physical measurement matrix (chest, waist, hip, inseam, height) compared against scraped garment size charts
6. Mix-match compatibility scored via cosine similarity of FashionCLIP embeddings; style coherence enforced via color palette analysis
7. All body scan data and wardrobe images remain local â€” zero cloud upload without explicit opt-in consent
8. Pluggable LLM backend: Claude API â†’ GPT-4V â†’ local Ollama, with graceful fallback chain

## External LLM API Integrations
| Provider | Model | Purpose | Config Key |
|----------|-------|---------|------------|
| Anthropic Claude | claude-opus-4-8 | Advanced styling consultation, outfit narrative generation | `ANTHROPIC_API_KEY` |
| OpenAI GPT-4V | gpt-4o | Complex garment attribute extraction from ambiguous product images | `OPENAI_API_KEY` |
| Local Ollama | phi3:mini | Offline styling suggestions, wardrobe Q&A, size advice | `OLLAMA_HOST` |

## HuggingFace Models in Use
| Model ID | Purpose | Link |
|----------|---------|------|
| `levihsu/OOTDiffusion` | Primary virtual try-on â€” diffusion-based, realistic fabric drape | https://huggingface.co/levihsu/OOTDiffusion |
| `facebook/densepose_rcnn_R_101_FPN_s1x` | Body pose estimation and UV surface mapping | https://huggingface.co/facebook/densepose |
| `patrickjohncyh/fashion-clip` | Garment embedding for compatibility scoring and wardrobe search | https://huggingface.co/patrickjohncyh/fashion-clip |
| `Salesforce/blip2-opt-2.7b` | Garment description and attribute extraction from product images | https://huggingface.co/Salesforce/blip2-opt-2.7b |
| `naver-clova-ix/donut-base` | Size chart OCR extraction from product pages | https://huggingface.co/naver-clova-ix/donut-base |
| `lllyasviel/ControlNet` | Pose-conditioned garment generation control | https://huggingface.co/lllyasviel/ControlNet |

## Current Active Development Tasks
- [ ] Initialize Python virtual environment (Python 3.11) and install core ML dependencies
- [ ] Implement camera body scanning pipeline using DensePose
- [ ] Build 3D body measurement extraction from DensePose output
- [ ] Build wardrobe catalog ingestion: photo â†’ BLIP-2 description â†’ FashionCLIP embedding â†’ SQLite
- [ ] Integrate OOTDiffusion for virtual try-on inference
- [ ] Develop browser extension (Manifest V3) for e-commerce product capture
- [ ] Implement size matching algorithm with measurement matrix
- [ ] Build mix-match recommendation engine using FashionCLIP cosine similarity
- [ ] Integrate local Ollama (Phi-3-mini) for offline styling advisor
- [ ] Add Claude API consultation layer with graceful fallback

## Related Documentation
- [`PROJECT-detail.md`](./PROJECT-detail.md) â€” Full technical specification and feature list
- [`PROJECT-DEVELOPMENT-PHASE-TRACKING.md`](./PROJECT-DEVELOPMENT-PHASE-TRACKING.md) â€” Phase-by-phase development roadmap
- [`SECOND-KNOWLEDGE-BRAIN.md`](./SECOND-KNOWLEDGE-BRAIN.md) â€” Self-improving research knowledge base


