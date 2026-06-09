# SECOND-KNOWLEDGE-BRAIN.md — wardrobe-twin-agent
## Self-Improving Research Knowledge Base

**Domain:** Virtual Try-On (VTON) · 3D Body Estimation · Fashion AI · Outfit Compatibility
**Last Updated:** 2026-06-03
**Update Frequency:** Weekly (automated crawler via crawl4ai)

---

## Core Concepts & Theoretical Foundations

### 1. Virtual Try-On (VTON)
Virtual try-on (VTON) is the task of synthesizing a realistic image of a target person wearing a specific garment. The field has evolved through three generations:
- **Warping-based methods (2018–2021):** Geometric transformation of garment image to fit body silhouette (e.g., CP-VTON, ACGPN). Fast but lacks realism for complex fabrics.
- **Flow-based methods (2021–2022):** Optical flow field predicts per-pixel garment deformation (e.g., VITON-HD, HR-VITON). Better wrinkle modeling.
- **Diffusion-based methods (2023–present):** Treat try-on as conditional image generation. Realistic fabric drape, texture preservation. State of the art as of 2024. Key models: OOTDiffusion, LaDI-VTON, CatVTON.

### 2. 3D Body Estimation
- **DensePose:** Maps 2D image pixels to 3D body surface coordinates (UV map). Developed by Facebook AI. Enables spatially-aware garment placement.
- **SMPL (Skinned Multi-Person Linear Model):** Parametric 3D body shape model. Encodes body shape with β parameters and pose with θ parameters. Used for 3D avatar generation.
- **SMPL-X:** Extended SMPL with expressive hands and face. More detailed but computationally heavier.
- **HMR2 (Human Mesh Recovery 2.0):** Transformer-based approach for real-time 3D body reconstruction from single image.

### 3. Outfit Compatibility Modeling
- **Complementary compatibility:** Items that go well together (top + bottom + shoes)
- **Visual compatibility:** Color harmony, pattern matching, style coherence
- **Occasion compatibility:** Contextual appropriateness (formal/casual/athletic)
- **Embedding-based scoring:** FashionCLIP, CLIP, or outfit-trained contrastive models map garments to embedding space where compatible items cluster together

### 4. Garment Representation
- **Semantic segmentation:** Segment garment from background (U-2-Net, SAM)
- **Attribute recognition:** Fine-grained classification of color, pattern, category, sleeve length, neckline, material
- **CLIP-based zero-shot:** Use CLIP or FashionCLIP for zero-shot attribute recognition without labeled data

### 5. Size Standardization Problem
- No ISO standard for clothing sizes; brand-specific variation is large (±4cm per size letter)
- Size charts typically specify: chest, waist, hip, inseam measurements per size letter
- Fit prediction requires: body measurement matrix + garment ease allowance + stretch factor
- Ease allowance: intentional gap between body measurement and garment measurement for comfort

---

## Key Research Papers

| Title | Authors | Year | Venue | Link | Relevance |
|-------|---------|------|-------|------|-----------|
| OOTDiffusion: Outfitting Fusion based Latent Diffusion for Controllable Virtual Try-on | Xu et al. | 2024 | arXiv | https://arxiv.org/abs/2403.01779 | Primary VTON model used in this project |
| VITON-HD: High-Resolution Virtual Try-On via Misalignment-Aware Normalization | Choi et al. | 2021 | CVPR | https://arxiv.org/abs/2103.16874 | Foundational HR try-on; dataset source |
| HR-VITON: High-Resolution Virtual Try-On with Misalignment and Occlusion-Handled Conditions | Lee et al. | 2022 | ECCV | https://arxiv.org/abs/2206.14180 | Flow-based VTON; fallback model |
| LaDI-VTON: Latent Diffusion Textual Inversion for Virtual Try-On | Morelli et al. | 2023 | ACM MM | https://arxiv.org/abs/2305.13501 | Text-conditioned try-on; advanced styling |
| DensePose: Dense Human Pose Estimation in the Wild | Güler et al. | 2018 | CVPR | https://arxiv.org/abs/1802.00434 | Body surface estimation; core component |
| Keeping Your Eye on the Ball: Trajectory Attention in Video Transformers | — | — | — | — | — |
| ViTPose: Simple Vision Transformer Baselines for Human Pose Estimation | Xu et al. | 2022 | NeurIPS | https://arxiv.org/abs/2204.12484 | Keypoint detection for pose conditioning |
| BLIP-2: Bootstrapping Language-Image Pre-training | Li et al. | 2023 | ICML | https://arxiv.org/abs/2301.12597 | Garment description extraction |
| Learning Fashion Compatibility with Bidirectional LSTMs | Han et al. | 2017 | ACM MM | https://arxiv.org/abs/1707.05691 | Foundational outfit compatibility work |
| FashionCLIP: Connecting Language and Images for Product Representations | Chia et al. | 2022 | arXiv | https://arxiv.org/abs/2204.03972 | Fashion-specific CLIP; garment embedding |
| Outfit Compatibility Prediction and Diagnosis with Multi-Layered Comparison Network | Lin et al. | 2020 | ACM MM | https://arxiv.org/abs/2007.08272 | Compatibility modeling; fine-grained |
| SMPL: A Skinned Multi-Person Linear Model | Loper et al. | 2015 | ACM TOG | https://dl.acm.org/doi/10.1145/2816795.2818013 | 3D body parameterization |
| TryOnDiffusion: A Tale of Two UNets | Zhu et al. | 2023 | CVPR | https://arxiv.org/abs/2306.08276 | Google's parallel try-on diffusion model |
| CatVTON: Concatenation Is All You Need for Virtual Try-On | Zheng et al. | 2024 | arXiv | https://arxiv.org/abs/2407.15886 | Simplified diffusion-based VTON; efficient |
| Segment Anything | Kirillov et al. | 2023 | ICCV | https://arxiv.org/abs/2304.02643 | Garment background removal; zero-shot segmentation |
| OCR-free Document Understanding Transformer (Donut) | Kim et al. | 2022 | ECCV | https://arxiv.org/abs/2111.15664 | Size chart OCR parsing |

---

## State-of-the-Art ML/DL Models

### Virtual Try-On Models
| Model | HuggingFace ID | Benchmark | Notes |
|-------|---------------|-----------|-------|
| OOTDiffusion | `levihsu/OOTDiffusion` | SSIM 0.85 on VITON-HD | **Primary model** — best quality/speed balance |
| CatVTON | `zhengchong/CatVTON` | SSIM 0.87 on VITON-HD | Simpler architecture; faster inference |
| TryOnDiffusion | (Google Research, not public) | — | Google's model; no public weights |
| HR-VITON | `sangyun-han/HR-VITON` | SSIM 0.82 | Flow-based fallback |
| LaDI-VTON | `miccunifi/ladi-vton` | SSIM 0.83 | Text-conditioned try-on |

### Body Estimation Models
| Model | HuggingFace ID | Task | Notes |
|-------|---------------|------|-------|
| DensePose RCNN | `facebook/densepose_rcnn_R_101_FPN_s1x` | UV surface estimation | Core component; requires detectron2 |
| ViTPose-B | `ViTPose-B` | Keypoint detection | 17-keypoint body pose |
| HMR2 | `geopavlakos/4DHumans` | 3D mesh recovery | SMPL-X output; high accuracy |

### Garment Understanding Models
| Model | HuggingFace ID | Task | Notes |
|-------|---------------|------|-------|
| FashionCLIP | `patrickjohncyh/fashion-clip` | Garment embedding | 512-dim; trained on 700K fashion items |
| BLIP-2 (2.7B) | `Salesforce/blip2-opt-2.7b` | Caption/VQA | Garment description |
| SAM (Segment Anything) | `facebook/sam-vit-huge` | Background removal | Zero-shot garment segmentation |
| Donut | `naver-clova-ix/donut-base` | Document OCR | Size chart extraction |
| CLIP (openai) | `openai/clip-vit-large-patch14` | Zero-shot classification | Style/attribute classification |

### Papers With Code Benchmarks
- **VITON-HD dataset benchmark:** https://paperswithcode.com/sota/virtual-try-on-on-viton-hd
- **DeepFashion benchmark:** https://paperswithcode.com/sota/fashion-compatibility-on-polyvore-outfits

---

## Tools, Libraries & Frameworks

| Tool | GitHub / Link | Use Case |
|------|-------------|----------|
| detectron2 | https://github.com/facebookresearch/detectron2 | DensePose inference |
| diffusers | https://github.com/huggingface/diffusers | OOTDiffusion inference pipeline |
| transformers | https://github.com/huggingface/transformers | BLIP-2, Donut, FashionCLIP |
| segment-anything | https://github.com/facebookresearch/segment-anything | Background removal |
| OpenCV | https://github.com/opencv/opencv-python | Webcam capture, image preprocessing |
| ControlNet | https://github.com/lllyasviel/ControlNet | Pose-conditioned generation |
| Ollama | https://github.com/ollama/ollama | Local LLM inference (Phi-3-mini) |
| crawl4ai | https://github.com/unclecode/crawl4ai | Knowledge brain auto-update crawler |
| FastAPI | https://github.com/tiangolo/fastapi | Local REST/WebSocket API server |
| electron | https://github.com/electron/electron | Desktop app packaging |
| sqlcipher3 | https://github.com/coleifer/sqlcipher3 | AES-256 encrypted SQLite |
| anthropic-sdk | https://github.com/anthropics/anthropic-sdk-python | Claude API integration |
| Polyvore Outfits | https://github.com/mvasil/fashion-compatibility | Outfit compatibility training data |
| VITON-HD Dataset | https://github.com/shadow2496/VITON-HD | Try-on training/evaluation data |
| DeepFashion2 | https://github.com/switchablenorms/DeepFashion2 | Garment detection dataset |

---

## Self-Update Protocol

### Crawler Configuration (crawl4ai)

```python
# crawler_config.py — wardrobe-twin-agent knowledge updater

CRAWL_TARGETS = [
    # ArXiv categories
    {"source": "arxiv", "categories": ["cs.CV", "cs.LG"],
     "queries": [
         "virtual try-on diffusion 2025",
         "clothing fitting 3D body estimation",
         "outfit compatibility fashion AI",
         "garment generation neural network"
     ]},

    # HuggingFace Papers
    {"source": "huggingface_papers",
     "tags": ["virtual-try-on", "fashion", "body-pose", "garment"]},

    # Papers With Code
    {"source": "papers_with_code",
     "tasks": [
         "virtual-try-on",
         "human-pose-estimation",
         "fashion-compatibility"
     ]},

    # Fashion Tech Blogs
    {"source": "web",
     "urls": [
         "https://research.google/blog/",  # filter for fashion/vision posts
         "https://ai.facebook.com/blog/",  # filter for vision/fashion
     ]},
]

UPDATE_FREQUENCY = "weekly"  # every Monday 02:00 local time
OUTPUT_FILE = "D:/Dungchan/7/SECOND-KNOWLEDGE-BRAIN.md"
```

### Domain-Specific Search Queries
```
ArXiv queries (cs.CV):
  - "virtual try-on diffusion model 2024 2025"
  - "outfit outfit compatibility recommendation deep learning"
  - "3D body shape estimation single image"
  - "garment segmentation zero-shot"
  - "clothing size prediction measurement"

Google Scholar:
  - "fashion AI e-commerce personalization"
  - "digital twin clothing retail"

HuggingFace Model Hub:
  - tag:virtual-try-on
  - tag:fashion-generation
  - task:image-to-image (filter fashion-related)
```

### Format for New Entries

**Research Papers:**
```markdown
| [Title] | [Authors] | [Year] | [Venue] | [DOI/arXiv] | [Relevance note] |
<!-- Added: YYYY-MM-DD by crawler -->
```

**New Models:**
```markdown
| [Model Name] | `[huggingface/model-id]` | [Benchmark score] | [Notes] |
<!-- Added: YYYY-MM-DD by crawler -->
```

**Update Frequency:** Weekly (every Monday)
**Deduplication:** Check paper title + arXiv ID against existing entries before adding

---

## Knowledge Update Log

| Date | Source | Items Added | Summary |
|------|--------|------------|---------|
| 2026-06-03 | Manual | 15 papers, 10 models, 12 tools | Initial knowledge base populated |
| — | — | — | Next update: automated crawler (Phase 4) |

---

## Quick Reference: Key Benchmarks

### VITON-HD Dataset Results (higher = better)
| Method | SSIM ↑ | FID ↓ | LPIPS ↓ |
|--------|--------|-------|---------|
| OOTDiffusion | 0.85 | 12.4 | 0.06 |
| CatVTON | 0.87 | 11.2 | 0.05 |
| HR-VITON | 0.82 | 15.6 | 0.09 |
| LaDI-VTON | 0.83 | 13.8 | 0.07 |

### Body Estimation (PCK@0.5 on COCO)
| Method | PCKh@0.5 ↑ |
|--------|-----------|
| ViTPose-B | 75.8 |
| HRNet-W32 | 74.9 |
| DensePose RCNN | — (different metric: GPS) |

### Outfit Compatibility (AUC on Polyvore Outfits)
| Method | AUC ↑ |
|--------|-------|
| FashionCLIP (zero-shot) | 0.81 |
| SCENet | 0.91 |
| MLCN | 0.88 |
| Bi-LSTM (Han 2017) | 0.76 |

---

## Domain Glossary

| Term | Definition |
|------|-----------|
| VTON | Virtual Try-On — synthesizing person wearing specific garment |
| UV Map | 2D texture coordinate map of 3D body surface (DensePose output) |
| SMPL | Skinned Multi-Person Linear Model — parametric 3D body |
| Ease allowance | Gap between body measurement and garment measurement (comfort factor) |
| FID | Fréchet Inception Distance — image generation quality metric (lower = better) |
| SSIM | Structural Similarity Index — image similarity metric (higher = better) |
| LPIPS | Learned Perceptual Image Patch Similarity (lower = better) |
| PCK | Percentage of Correct Keypoints — pose estimation accuracy metric |
| GPS | Geodesic Point Similarity — DensePose-specific accuracy metric |
| Zero-shot | Model predicts on categories not seen during training |
| Contrastive learning | Training by contrasting similar vs. dissimilar pairs (CLIP approach) |
