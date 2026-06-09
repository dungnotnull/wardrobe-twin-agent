"""Wardrobe catalog service.

Orchestrates the full pipeline:
  photo -> garment segmentation -> BLIP-2 description -> FashionCLIP embedding -> SQLite

Handles search, listing, CRUD, duplicate detection, and analytics.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from config.settings import settings
from backend.db.database import db
from backend.ml.garment_understanding.blip2_extractor import blip2_extractor
from backend.ml.garment_understanding.fashionclip_pipeline import fashionclip, EMBEDDING_DIM
from backend.ml.garment_understanding.garment_segmenter import garment_segmenter
from backend.core.models import WardrobeItemCreate, WardrobeItemRead, WardrobeItemUpdate

logger = logging.getLogger(__name__)

DUPLICATE_SIMILARITY_THRESHOLD = 0.92


class WardrobeCatalog:
    """Wardrobe catalog management service."""

    def add_item(self, item: WardrobeItemCreate, pin: str, image_bytes: bytes | None = None) -> WardrobeItemRead:
        """Add a garment to the wardrobe catalog."""
        if image_bytes is None and item.image_b64:
            image_bytes = base64.b64decode(item.image_b64)
        if image_bytes is None and item.image_url:
            image_bytes = self._download_image(item.image_url)
        if image_bytes is None:
            raise ValueError("No image data provided")

        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        item_id = str(uuid.uuid4())
        image_filename = f"{item_id}.png"
        image_path = settings.WARDROBE_IMG_DIR / image_filename

        # Segment garment (remove background)
        segmented = garment_segmenter.remove_background(pil_image)
        # Save original + segmented side by side or just the original
        pil_image.save(str(image_path))

        # BLIP-2 attribute extraction
        attrs = blip2_extractor.describe(pil_image)

        item_type = item.item_type or attrs.get("item_type", "unknown")
        color = item.color or attrs.get("color", "unknown")
        pattern = item.pattern or attrs.get("pattern", "unknown")
        style = item.style or attrs.get("style", "unknown")
        material = item.material or attrs.get("material", "unknown")
        season = item.season or "all"
        tags = attrs.get("tags", [])
        description = attrs.get("caption", "")

        # FashionCLIP embedding
        embedding = fashionclip.embed_image(pil_image)
        embedding_bytes = embedding.tobytes()

        # Check for duplicates
        duplicates = self._check_duplicates(embedding, item_id)

        db.insert_wardrobe_item({
            "id": item_id, "image_path": image_filename, "image_blob": image_bytes,
            "description": description, "tags": json.dumps(tags),
            "item_type": item_type, "color": color, "pattern": pattern,
            "style": style, "material": material, "season": season,
            "embedding": embedding_bytes, "brand": item.brand,
            "size_label": item.size_label, "purchase_date": item.purchase_date,
            "purchase_price": item.purchase_price,
        }, pin=pin)

        result = WardrobeItemRead(
            id=item_id, image_path=image_filename, description=description,
            tags=tags, item_type=item_type, color=color, pattern=pattern,
            style=style, material=material, season=season, brand=item.brand,
            size_label=item.size_label, purchase_price=item.purchase_price,
        )
        if duplicates:
            logger.info("Potential duplicates found for item %s: %s", item_id, duplicates)
        return result

    def add_item_batch(self, images: list[tuple[str, bytes]], pin: str, defaults: WardrobeItemCreate | None = None) -> list[WardrobeItemRead]:
        """Batch add multiple garments. Each tuple is (filename, image_bytes)."""
        results = []
        for filename, img_bytes in images:
            try:
                item = defaults or WardrobeItemCreate()
                result = self.add_item(item, pin=pin, image_bytes=img_bytes)
                results.append(result)
                logger.info("Cataloged: %s -> %s", filename, result.id)
            except Exception as e:
                logger.error("Failed to catalog %s: %s", filename, e)
        return results

    def update_item(self, item_id: str, updates: WardrobeItemUpdate) -> WardrobeItemRead | None:
        """Update wardrobe item attributes."""
        update_dict = updates.model_dump(exclude_none=True)
        if update_dict.get("tags") and isinstance(update_dict["tags"], list):
            update_dict["tags"] = json.dumps(update_dict["tags"])
        db.update_wardrobe_item(item_id, update_dict)
        return self.get_item(item_id)

    def get_item(self, item_id: str, pin: str | None = None) -> WardrobeItemRead | None:
        row = db.get_wardrobe_item(item_id, pin=pin)
        if row is None:
            return None
        return self._row_to_read(row)

    def list_items(self, item_type: str | None = None, color: str | None = None, season: str | None = None, brand: str | None = None, limit: int = 100, offset: int = 0) -> list[WardrobeItemRead]:
        rows = db.list_wardrobe_items(item_type=item_type, color=color, season=season, brand=brand, limit=limit, offset=offset)
        return [self._row_to_read(r) for r in rows]

    def search_by_text(self, query: str, top_k: int = 10) -> list[WardrobeItemRead]:
        query_embedding = fashionclip.embed_text(query)
        results = db.search_wardrobe_by_embedding(query_embedding.tobytes(), top_k=top_k)
        return [self._row_to_read(r) for r in results]

    def search_by_image(self, image: Image.Image, top_k: int = 10) -> list[dict]:
        query_embedding = fashionclip.embed_image(image)
        return db.search_wardrobe_by_embedding(query_embedding.tobytes(), top_k=top_k)

    def delete_item(self, item_id: str) -> bool:
        return db.delete_wardrobe_item(item_id)

    def get_all_embeddings(self) -> list[tuple[str, np.ndarray]]:
        rows = db.get_all_embeddings()
        return [(item_id, np.frombuffer(emb, dtype=np.float32)) for item_id, emb in rows]

    def _check_duplicates(self, embedding: np.ndarray, skip_id: str) -> list[str]:
        """Check for near-duplicate items in the wardrobe."""
        if embedding.sum() == 0:
            return []
        all_embs = self.get_all_embeddings()
        duplicates = []
        for item_id, emb in all_embs:
            if item_id == skip_id:
                continue
            sim = fashionclip.cosine_similarity(embedding, emb)
            if sim > DUPLICATE_SIMILARITY_THRESHOLD:
                duplicates.append(item_id)
        return duplicates

    def get_analytics(self) -> dict:
        """Compute wardrobe analytics for the dashboard."""
        from collections import Counter
        items = db.list_wardrobe_items(limit=10000)
        if not items:
            return {"total_items": 0}

        type_counts: dict[str, int] = Counter(r.get("item_type", "unknown") for r in items)
        color_counts: dict[str, int] = Counter(r.get("color", "unknown") for r in items)
        season_counts: dict[str, int] = Counter(r.get("season", "all") for r in items)

        total_value = sum(r.get("purchase_price") or 0 for r in items)
        total_worn = sum(r.get("worn_count", 0) for r in items)
        avg_cpw = total_value / max(total_worn, 1)

        most_worn = sorted(items, key=lambda r: r.get("worn_count", 0), reverse=True)[:5]
        least_worn = [r for r in items if r.get("worn_count", 0) == 0][:5]

        # Find duplicate groups
        all_embs = self.get_all_embeddings()
        duplicate_groups = self._find_duplicate_groups(all_embs)

        return {
            "total_items": len(items), "items_by_type": dict(type_counts),
            "items_by_color": dict(color_counts), "items_by_season": dict(season_counts),
            "most_worn": [{"id": r["id"], "type": r.get("item_type"), "count": r.get("worn_count")} for r in most_worn],
            "least_worn": [{"id": r["id"], "type": r.get("item_type")} for r in least_worn],
            "total_value": total_value, "avg_cost_per_wear": round(avg_cpw, 2),
            "duplicate_groups": duplicate_groups,
            "color_palette": [c for c, _ in color_counts.most_common(8)],
        }

    def _find_duplicate_groups(self, all_embs: list[tuple[str, np.ndarray]]) -> list[list[str]]:
        """Find groups of near-duplicate items using transitive similarity."""
        if not all_embs:
            return []
        visited: set[str] = set()
        groups: list[list[str]] = []
        for i, (id_a, emb_a) in enumerate(all_embs):
            if id_a in visited:
                continue
            group = [id_a]
            visited.add(id_a)
            for j, (id_b, emb_b) in enumerate(all_embs):
                if id_b in visited or j <= i:
                    continue
                sim = fashionclip.cosine_similarity(emb_a, emb_b)
                if sim > DUPLICATE_SIMILARITY_THRESHOLD:
                    group.append(id_b)
                    visited.add(id_b)
            if len(group) > 1:
                groups.append(group)
        return groups

    @staticmethod
    def _download_image(url: str) -> bytes | None:
        import httpx
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            logger.warning("Failed to download image from %s: %s", url, e)
        return None

    @staticmethod
    def _row_to_read(row: dict) -> WardrobeItemRead:
        tags = row.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError):
                tags = [tags] if tags else []
        return WardrobeItemRead(
            id=row["id"], image_path=row.get("image_path"),
            description=row.get("description"), tags=tags if isinstance(tags, list) else [],
            item_type=row.get("item_type"), color=row.get("color"),
            pattern=row.get("pattern"), style=row.get("style"),
            material=row.get("material"), season=row.get("season"),
            brand=row.get("brand"), size_label=row.get("size_label"),
            purchase_price=row.get("purchase_price"),
            worn_count=row.get("worn_count", 0),
            similarity=row.get("similarity"),
            created_at=row.get("created_at"),
        )


wardrobe_catalog = WardrobeCatalog()
