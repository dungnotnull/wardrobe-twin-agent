"""User learning loops: style preferences, brand size calibration, worn tracking, monthly reports."""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from typing import Any

from backend.db.database import db
from backend.core.models import OutfitFeedback, StylePreferenceUpdate, StyleProfileRead, MonthlyReport

logger = logging.getLogger(__name__)


class StyleLearningEngine:
    """Learn user preferences from outfit feedback and update style profile."""

    def update_style_from_feedback(self, profile_id: str, feedback: OutfitFeedback) -> None:
        outfit = db.conn.execute("SELECT item_ids, occasion FROM outfit_logs WHERE id = ?", (feedback.outfit_id,)).fetchone()
        if not outfit:
            return

        item_ids = json.loads(outfit["item_ids"])
        liked = feedback.liked

        items = []
        for iid in item_ids:
            row = db.conn.execute("SELECT color, item_type, style, tags FROM wardrobe_items WHERE id = ?", (iid,)).fetchone()
            if row:
                items.append(dict(row))

        current = db.get_style_profile(profile_id) or {}
        preferred_colors = set(current.get("preferred_colors", []) or [])
        preferred_styles = set(current.get("preferred_styles", []) or [])
        avoid_patterns = set(current.get("avoid_patterns", []) or [])

        for item in items:
            color = item.get("color", "")
            style = item.get("style", "")
            tags = item.get("tags", "")
            if isinstance(tags, str):
                try:
                    tags_list = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = [tags] if tags else []
            else:
                tags_list = tags if isinstance(tags, list) else []

            if liked:
                if color:
                    preferred_colors.add(color)
                if style:
                    preferred_styles.add(style)
                for tag in tags_list:
                    preferred_styles.add(tag)
            else:
                if color:
                    avoid_patterns.add(color)
                if style:
                    avoid_patterns.add(style)
                preferred_colors.discard(color)
                preferred_styles.discard(style)

        db.upsert_style_profile(profile_id, {
            "preferred_colors": list(preferred_colors),
            "preferred_styles": list(preferred_styles),
            "avoid_patterns": list(avoid_patterns),
            "formality_preference": current.get("formality_preference"),
            "brand_affinities": current.get("brand_affinities", {}),
            "size_corrections": current.get("size_corrections", {}),
        })

    def update_style_from_preferences(self, profile_id: str, update: StylePreferenceUpdate) -> None:
        current = db.get_style_profile(profile_id) or {}
        preferred_colors = set(current.get("preferred_colors", []) or [])
        preferred_styles = set(current.get("preferred_styles", []) or [])
        avoid_patterns = set(current.get("avoid_patterns", []) or [])

        if update.preferred_colors:
            preferred_colors.update(update.preferred_colors)
        if update.preferred_styles:
            preferred_styles.update(update.preferred_styles)
        if update.avoid_patterns:
            avoid_patterns.update(update.avoid_patterns)

        db.upsert_style_profile(profile_id, {
            "preferred_colors": list(preferred_colors),
            "preferred_styles": list(preferred_styles),
            "avoid_patterns": list(avoid_patterns),
            "formality_preference": update.formality_preference or current.get("formality_preference"),
            "brand_affinities": current.get("brand_affinities", {}),
            "size_corrections": current.get("size_corrections", {}),
        })

    def record_worn(self, item_ids: list[str], occasion: str | None = None, rating: int | None = None) -> str:
        return db.insert_outfit_log({
            "item_ids": item_ids, "occasion": occasion,
            "rating": rating, "liked": None, "worn_date": datetime.utcnow().isoformat(),
        })

    def generate_monthly_report(self, profile_id: str, month: str | None = None) -> MonthlyReport:
        if month is None:
            month = datetime.utcnow().strftime("%Y-%m")

        items = db.list_wardrobe_items(limit=10000)
        outfits = db.get_outfit_logs(limit=500)

        items_this_month = [i for i in items if i.get("created_at", "").startswith(month)]
        outfits_this_month = [o for o in outfits if o.get("worn_date", "").startswith(month) or o.get("created_at", "").startswith(month)]

        # Find underused items (never worn)
        underused = [i for i in items if i.get("worn_count", 0) == 0]

        # Brand size corrections
        corrections = db.get_brand_size_corrections(profile_id)
        brand_corr = {brand: list(fits.values())[0] if fits else "unknown" for brand, fits in corrections.items()}

        # Top outfits by rating
        top_outfits = sorted(outfits_this_month, key=lambda o: o.get("rating", 0) or 0, reverse=True)[:5]

        # Compute style drift
        current_colors = Counter(i.get("color", "unknown") for i in items_this_month) if items_this_month else Counter()
        style_drift = len(current_colors) / max(len(items_this_month), 1)

        total_value = sum(i.get("purchase_price") or 0 for i in items)
        total_worn = sum(i.get("worn_count", 0) for i in items)
        avg_cpw = total_value / max(total_worn, 1)

        return MonthlyReport(
            month=month, items_added=len(items_this_month),
            items_worn=sum(1 for o in outfits_this_month if o.get("worn_date")),
            outfits_created=len(outfits_this_month),
            top_outfits=[{"id": o.get("id"), "items": o.get("item_ids"), "rating": o.get("rating")} for o in top_outfits],
            underused_items=[{"id": i["id"], "type": i.get("item_type"), "color": i.get("color")} for i in underused[:10]],
            brand_size_corrections=brand_corr,
            style_drift_score=round(style_drift, 3),
            cost_per_wear_avg=round(avg_cpw, 2),
        )


style_learning = StyleLearningEngine()
