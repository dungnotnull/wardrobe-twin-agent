"""Size matching engine.

Compares user body measurements against a garment's size chart to recommend
the best-fitting size with confidence score and fit notes.
Incorporates brand size correction factors from purchase history.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.core.models import BodyMeasurements, SizeChartEntry, SizeMatchResult
from backend.db.database import db

logger = logging.getLogger(__name__)

EASE_ALLOWANCES: dict[str, float] = {
    "upper_body": 4.0,
    "lower_body": 2.5,
    "dresses": 3.5,
}

TOLERANCE_CM = 3.0

# Measurement keys relevant per garment category
CATEGORY_MEASUREMENTS = {
    "upper_body": ["chest_cm", "waist_cm", "shoulder_cm"],
    "lower_body": ["waist_cm", "hip_cm", "inseam_cm"],
    "dresses": ["chest_cm", "waist_cm", "hip_cm"],
}


class SizeMatchingEngine:
    """Recommend garment size by comparing body measurements to size chart."""

    def match(self, measurements: BodyMeasurements, size_chart: list[SizeChartEntry], category: str = "upper_body", brand: str | None = None, profile_id: str | None = None) -> SizeMatchResult:
        """Find best size match using measurement diff with ease allowances."""
        if not size_chart:
            return SizeMatchResult(recommended_size="Unknown", confidence=0.0, fit_notes=["No size chart data available"])

        ease = EASE_ALLOWANCES.get(category, 3.0)
        brand_correction = self._get_brand_correction(profile_id, brand)
        relevant_keys = CATEGORY_MEASUREMENTS.get(category, ["chest_cm", "waist_cm"])

        best_size = ""
        best_score = float("inf")
        best_diffs: dict[str, float] = {}
        all_diffs: dict[str, dict[str, float]] = {}

        for entry in size_chart:
            diffs: dict[str, float] = {}
            total_diff = 0.0
            n_dims = 0

            for key in relevant_keys:
                body_val = getattr(measurements, key, None)
                garment_val = getattr(entry, key, None)

                if body_val is not None and garment_val is not None and garment_val > 0:
                    corrected_body = body_val + self._get_correction(brand_correction, key)
                    diff = (corrected_body + ease) - garment_val
                    diffs[key] = round(diff, 2)
                    total_diff += abs(diff)
                    n_dims += 1

            avg_diff = total_diff / max(n_dims, 1)
            all_diffs[entry.size_label] = diffs

            if avg_diff < best_score:
                best_score = avg_diff
                best_size = entry.size_label
                best_diffs = diffs

        confidence = max(0.1, min(1.0, 1.0 - (best_score / 15.0)))
        fit_notes = self._generate_fit_notes(best_diffs)

        return SizeMatchResult(
            recommended_size=best_size,
            confidence=round(confidence, 2),
            fit_notes=fit_notes,
            diff_matrix=all_diffs,
        )

    @staticmethod
    def _get_brand_correction(profile_id: str | None, brand: str | None) -> dict[str, str]:
        if not profile_id or not brand:
            return {}
        try:
            corrections = db.get_brand_size_corrections(profile_id)
            return corrections.get(brand, {})
        except Exception:
            return {}

    @staticmethod
    def _get_correction(corrections: dict[str, str], key: str) -> float:
        """Return a cm offset based on brand correction data."""
        fit = corrections.get(key, corrections.get("default", ""))
        if fit == "tight":
            return -1.0
        if fit == "loose":
            return 1.0
        return 0.0

    @staticmethod
    def _generate_fit_notes(diffs: dict[str, float]) -> list[str]:
        notes: list[str] = []
        for key, diff in diffs.items():
            label = key.replace("_cm", "").replace("_", " ")
            if diff > TOLERANCE_CM:
                notes.append(f"Will be tight on {label} (garment is {abs(diff):.1f}cm too small)")
            elif diff < -TOLERANCE_CM:
                notes.append(f"Loose on {label} ({abs(diff):.1f}cm extra room)")
            elif abs(diff) <= 1.0:
                notes.append(f"Perfect fit on {label}")
            else:
                notes.append(f"Good fit on {label} (within {abs(diff):.1f}cm)")
        return notes


size_matcher = SizeMatchingEngine()
