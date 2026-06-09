"""Mix-match recommendation engine.

Given a garment, finds compatible items in the wardrobe using
FashionCLIP cosine similarity + HSV color harmony analysis.
Generates complete outfit combinations and supports 'complete the look'.
"""
from __future__ import annotations

import colorsys
import logging
from collections import defaultdict
from typing import Any

import numpy as np
from PIL import Image

from config.settings import settings
from backend.core.models import MixMatchRequest, MixMatchResult, MixMatchResponse
from backend.core.wardrobe_catalog import wardrobe_catalog
from backend.ml.garment_understanding.fashionclip_pipeline import fashionclip
from backend.db.database import db

logger = logging.getLogger(__name__)

SIMILARITY_WEIGHT = 0.55
COLOR_HARMONY_WEIGHT = 0.25
TYPE_COMPATIBILITY_WEIGHT = 0.20

HUE_MAP = {
    "red": 0.0, "orange": 30.0, "yellow": 60.0, "green": 120.0,
    "teal": 180.0, "blue": 240.0, "purple": 270.0, "pink": 330.0,
    "black": -1.0, "white": -1.0, "gray": -1.0, "neutral": -1.0,
    "beige": -1.0, "brown": 30.0, "navy": 240.0, "burgundy": 345.0,
    "khaki": 55.0, "olive": 75.0, "coral": 15.0, "maroon": 350.0,
    "cream": -1.0, "tan": 40.0,
}

# Type compatibility matrix: what goes well together
TYPE_SLOTS = {
    "top": {"shirt", "blouse", "t-shirt", "top", "sweater", "hoodie", "polo", "tank"},
    "outerwear": {"jacket", "blazer", "coat", "vest", "cardigan"},
    "bottom": {"pant", "jean", "trouser", "short", "skirt", "bottom", "chino"},
    "dress": {"dress", "jumpsuit", "romper"},
    "shoes": {"shoe", "boot", "sneaker", "sandal", "heel", "flat", "loafer"},
    "accessory": {"bag", "hat", "scarf", "belt", "watch", "jewelry", "sunglasses"},
}


class MixMatchEngine:
    """Outfit compatibility and mix-match recommendation engine."""

    def recommend(self, request: MixMatchRequest, pin: str | None = None) -> MixMatchResponse:
        """Find compatible wardrobe items for the given garment."""
        query_embedding = self._resolve_embedding(request)
        if query_embedding.sum() == 0:
            return MixMatchResponse(query_item="unknown", suggestions=[], outfit_combinations=[])

        all_embeddings = wardrobe_catalog.get_all_embeddings()
        if not all_embeddings:
            return MixMatchResponse(query_item="unknown", suggestions=[], outfit_combinations=[])

        # Compute similarities
        candidates = []
        for item_id, emb in all_embeddings:
            if request.garment_wardrobe_id and item_id == request.garment_wardrobe_id:
                continue
            sim = fashionclip.cosine_similarity(query_embedding, emb)
            candidates.append((item_id, sim, emb))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:request.top_k * 3]

        # Score with color harmony and type compatibility
        query_color = self._get_query_color(request)
        suggestions = []
        for item_id, sim, emb in top_candidates:
            item_row = db.conn.execute(
                "SELECT id, description, item_type, color, image_path, season FROM wardrobe_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if item_row is None:
                continue

            color_harmony = self._compute_color_harmony(query_color, item_row["color"] or "neutral")
            type_compat = self._compute_type_compatibility(request, item_row["item_type"] or "")
            overall = SIMILARITY_WEIGHT * sim + COLOR_HARMONY_WEIGHT * color_harmony + TYPE_COMPATIBILITY_WEIGHT * type_compat

            suggestions.append(MixMatchResult(
                item_id=item_id, item_type=item_row["item_type"],
                description=item_row["description"], color=item_row["color"],
                similarity=round(sim, 4), color_harmony=round(color_harmony, 4),
                overall_score=round(overall, 4), image_path=item_row["image_path"],
            ))

        suggestions.sort(key=lambda x: x.overall_score, reverse=True)
        suggestions = suggestions[:request.top_k]

        outfit_combos = self._generate_outfit_combinations(suggestions) if request.include_outfit_combos else []

        return MixMatchResponse(
            query_item=request.garment_wardrobe_id or "new_garment",
            suggestions=suggestions,
            outfit_combinations=outfit_combos,
        )

    def complete_the_look(self, existing_item_ids: list[str], missing_slots: list[str] | None = None) -> dict[str, list[MixMatchResult]]:
        """Fill missing outfit slots from wardrobe given existing items."""
        if not existing_item_ids:
            return {}

        occupied_slots = set()
        for item_id in existing_item_ids:
            row = db.conn.execute("SELECT item_type FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
            if row:
                slot = self._classify_type(row["item_type"] or "")
                if slot:
                    occupied_slots.add(slot)

        target_slots = missing_slots or ["top", "bottom", "outerwear", "shoes"]
        needed_slots = [s for s in target_slots if s not in occupied_slots]

        results: dict[str, list[MixMatchResult]] = {}
        all_embs = wardrobe_catalog.get_all_embeddings()
        if not all_embs:
            return results

        for slot in needed_slots:
            slot_candidates = []
            for item_id, emb in all_embs:
                if item_id in existing_item_ids:
                    continue
                row = db.conn.execute("SELECT item_type, color, description, image_path FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
                if not row:
                    continue
                item_slot = self._classify_type(row["item_type"] or "")
                if item_slot != slot:
                    continue
                # Score based on compatibility with existing items
                score = 0.0
                n = 0
                for existing_id in existing_item_ids:
                    existing_row = db.conn.execute("SELECT embedding FROM wardrobe_items WHERE id = ?", (existing_id,)).fetchone()
                    if existing_row and existing_row["embedding"]:
                        existing_emb = np.frombuffer(existing_row["embedding"], dtype=np.float32)
                        score += fashionclip.cosine_similarity(emb, existing_emb)
                        n += 1
                avg_score = score / max(n, 1) if n > 0 else 0.5

                slot_candidates.append(MixMatchResult(
                    item_id=item_id, item_type=row["item_type"],
                    description=row["description"], color=row["color"],
                    similarity=round(avg_score, 4), color_harmony=0.7,
                    overall_score=round(avg_score, 4), image_path=row["image_path"],
                ))

            slot_candidates.sort(key=lambda x: x.overall_score, reverse=True)
            results[slot] = slot_candidates[:3]

        return results

    def _resolve_embedding(self, request: MixMatchRequest) -> np.ndarray:
        if request.garment_embedding is not None:
            return np.array(request.garment_embedding, dtype=np.float32)
        if request.garment_wardrobe_id:
            row = db.conn.execute("SELECT embedding FROM wardrobe_items WHERE id = ?", (request.garment_wardrobe_id,)).fetchone()
            if row and row["embedding"]:
                return np.frombuffer(row["embedding"], dtype=np.float32)
        if request.garment_image_b64:
            import base64
            import io
            img_bytes = base64.b64decode(request.garment_image_b64)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            return fashionclip.embed_image(pil_img)
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    def _get_query_color(self, request: MixMatchRequest) -> str:
        if request.garment_wardrobe_id:
            row = db.conn.execute("SELECT color FROM wardrobe_items WHERE id = ?", (request.garment_wardrobe_id,)).fetchone()
            if row and row["color"]:
                return row["color"].lower()
        return "neutral"

    @staticmethod
    def _compute_color_harmony(color_a: str, color_b: str) -> float:
        hue_a = HUE_MAP.get(color_a.lower(), -1.0)
        hue_b = HUE_MAP.get(color_b.lower(), -1.0)

        if hue_a < 0 or hue_b < 0:
            return 0.7

        angle = abs(hue_a - hue_b)
        if angle > 180:
            angle = 360 - angle

        if angle <= 30:
            return 0.9
        elif angle <= 60:
            return 0.8
        elif 160 <= angle <= 200:
            return 0.7
        elif angle <= 90:
            return 0.6
        else:
            return 0.4

    @staticmethod
    def _compute_type_compatibility(request: MixMatchRequest, candidate_type: str) -> float:
        """Score type compatibility: complementary types score higher than same types."""
        if request.garment_wardrobe_id:
            row = db.conn.execute("SELECT item_type FROM wardrobe_items WHERE id = ?", (request.garment_wardrobe_id,)).fetchone()
            if row and row["item_type"]:
                query_type = row["item_type"].lower()
                candidate_lower = candidate_type.lower()
                if query_type == candidate_lower:
                    return 0.3  # Same type — less useful for mix-match
                query_slot = MixMatchEngine._classify_type(query_type)
                cand_slot = MixMatchEngine._classify_type(candidate_lower)
                complementary_pairs = {("top", "bottom"), ("bottom", "top"), ("top", "shoes"), ("bottom", "shoes"),
                                      ("dress", "shoes"), ("dress", "accessory"), ("top", "accessory"),
                                      ("outerwear", "bottom"), ("outerwear", "top")}
                if (query_slot, cand_slot) in complementary_pairs:
                    return 1.0
        return 0.5

    @staticmethod
    def _classify_type(item_type: str) -> str | None:
        t = item_type.lower()
        for slot, keywords in TYPE_SLOTS.items():
            if any(k in t for k in keywords):
                return slot
        return None

    @staticmethod
    def _generate_outfit_combinations(suggestions: list[MixMatchResult]) -> list[list[str]]:
        by_slot: dict[str, list[str]] = defaultdict(list)
        for s in suggestions:
            slot = MixMatchEngine._classify_type(s.item_type or "")
            if slot:
                by_slot[slot].append(s.item_id)

        combos: list[list[str]] = []
        if "dress" in by_slot:
            for d_id in by_slot["dress"][:3]:
                combo = [d_id]
                if "shoes" in by_slot:
                    combo.append(by_slot["shoes"][0])
                if "accessory" in by_slot:
                    combo.append(by_slot["accessory"][0])
                combos.append(combo)

        if "top" in by_slot and "bottom" in by_slot:
            for t_id in by_slot["top"][:2]:
                for b_id in by_slot["bottom"][:2]:
                    combo = [t_id, b_id]
                    if "outerwear" in by_slot:
                        combo.append(by_slot["outerwear"][0])
                    if "shoes" in by_slot:
                        combo.append(by_slot["shoes"][0])
                    combos.append(combo)
                    if len(combos) >= 8:
                        break
                if len(combos) >= 8:
                    break

        return combos[:8]


mix_match = MixMatchEngine()
