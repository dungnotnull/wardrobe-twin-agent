"""FashionCLIP embedding pipeline.

Generates 512-dim FashionCLIP embeddings for garment images and text,
used for wardrobe similarity search, mix-match compatibility scoring,
and zero-shot garment attribute classification.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512


class FashionCLIPPipeline:
    """FashionCLIP embedding generation, similarity scoring, and zero-shot classification."""

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            from transformers import CLIPModel, CLIPProcessor
            import torch
            self._processor = CLIPProcessor.from_pretrained(settings.FASHIONCLIP_MODEL_ID)
            self._model = CLIPModel.from_pretrained(settings.FASHIONCLIP_MODEL_ID)
            self._model.to(settings.effective_device)
            self._model.eval()
            logger.info("FashionCLIP model loaded on %s", settings.effective_device)
        except Exception as e:
            logger.warning("FashionCLIP load failed: %s", e)
            self._model = None
            self._processor = None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def embed_image(self, image: Image.Image | np.ndarray) -> np.ndarray:
        """Generate a 512-dim L2-normalized embedding for a garment image."""
        self._ensure_loaded()
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image if image.ndim == 3 else image)
        if self._model is not None and self._processor is not None:
            return self._embed_image_with_model(image)
        logger.warning("FashionCLIP unavailable, returning zero embedding")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    def _embed_image_with_model(self, image: Image.Image) -> np.ndarray:
        import torch
        inputs = self._processor(images=image, return_tensors="pt").to(settings.effective_device)
        with torch.no_grad():
            features = self._model.get_image_features(**inputs)
        embedding = features.cpu().numpy().flatten().astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding

    def embed_text(self, text: str) -> np.ndarray:
        """Generate a 512-dim L2-normalized embedding for a text query."""
        self._ensure_loaded()
        if self._model is not None and self._processor is not None:
            import torch
            inputs = self._processor(text=[text], return_tensors="pt", padding=True).to(settings.effective_device)
            with torch.no_grad():
                features = self._model.get_text_features(**inputs)
            embedding = features.cpu().numpy().flatten().astype(np.float32)
            norm = np.linalg.norm(embedding)
            return embedding / norm if norm > 0 else embedding
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    def embed_images_batch(self, images: list[Image.Image]) -> np.ndarray:
        """Batch embed multiple images. Returns shape (N, 512)."""
        self._ensure_loaded()
        if self._model is None or self._processor is None:
            return np.zeros((len(images), EMBEDDING_DIM), dtype=np.float32)
        import torch
        inputs = self._processor(images=images, return_tensors="pt", padding=True).to(settings.effective_device)
        with torch.no_grad():
            features = self._model.get_image_features(**inputs)
        embeddings = features.cpu().numpy().astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return embeddings / norms

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    @staticmethod
    def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Compute pairwise cosine similarity. Shapes: (N, D), (M, D) -> (N, M)."""
        a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
        return a_norm @ b_norm.T

    def zero_shot_classify(self, image: Image.Image, labels: list[str]) -> list[tuple[str, float]]:
        """Classify an image against a set of text labels using FashionCLIP zero-shot."""
        image_emb = self.embed_image(image)
        label_embs = np.array([self.embed_text(label) for label in labels])
        if image_emb.sum() == 0 or label_embs.sum() == 0:
            return [(label, 1.0 / len(labels)) for label in labels]
        similarities = [self.cosine_similarity(image_emb, le) for le in label_embs]
        exp_sims = np.exp(np.array(similarities))
        probs = exp_sims / exp_sims.sum()
        results = sorted(zip(labels, probs.tolist()), key=lambda x: x[1], reverse=True)
        return [(label, round(float(p), 4)) for label, p in results]

    def search(self, query_embedding: np.ndarray, candidate_embeddings: list[tuple[str, np.ndarray]], top_k: int = 10) -> list[tuple[str, float]]:
        scores = [(item_id, self.cosine_similarity(query_embedding, emb)) for item_id, emb in candidate_embeddings]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


fashionclip = FashionCLIPPipeline()
