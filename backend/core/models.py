"""Shared Pydantic data models for the entire application."""
from __future__ import annotations

import json
from datetime import datetime, date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class GarmentCategory(str, Enum):
    UPPER_BODY = "upper_body"
    LOWER_BODY = "lower_body"
    DRESSES = "dresses"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL = "all"


class FitQuality(str, Enum):
    TIGHT = "tight"
    PERFECT = "perfect"
    LOOSE = "loose"


class AdvisorSource(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"
    FALLBACK = "fallback"


# ── Body profile ───────────────────────────────────────────────


class BodyMeasurements(BaseModel):
    height_cm: float | None = None
    weight_kg: float | None = None
    chest_cm: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    inseam_cm: float | None = None
    shoulder_cm: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        return self.model_dump()


class BodyProfileCreate(BaseModel):
    label: str = "default"
    measurements: BodyMeasurements
    webcam_frame_b64: str | None = None


class BodyProfileRead(BaseModel):
    id: str
    label: str
    measurements: BodyMeasurements
    has_avatar: bool = False
    has_uv_map: bool = False
    created_at: str | None = None
    updated_at: str | None = None


# ── Wardrobe item ──────────────────────────────────────────────


class WardrobeItemCreate(BaseModel):
    image_b64: str | None = None
    image_url: str | None = None
    item_type: str | None = None
    color: str | None = None
    pattern: str | None = None
    style: str | None = None
    material: str | None = None
    season: str | None = None
    brand: str | None = None
    size_label: str | None = None
    purchase_date: str | None = None
    purchase_price: float | None = None


class WardrobeItemUpdate(BaseModel):
    item_type: str | None = None
    color: str | None = None
    pattern: str | None = None
    style: str | None = None
    material: str | None = None
    season: str | None = None
    brand: str | None = None
    size_label: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class WardrobeItemRead(BaseModel):
    id: str
    image_path: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    item_type: str | None = None
    color: str | None = None
    pattern: str | None = None
    style: str | None = None
    material: str | None = None
    season: str | None = None
    brand: str | None = None
    size_label: str | None = None
    purchase_price: float | None = None
    worn_count: int = 0
    similarity: float | None = None
    created_at: str | None = None


# ── Try-on ─────────────────────────────────────────────────────


class TryOnRequest(BaseModel):
    profile_id: str
    garment_image_b64: str | None = None
    garment_wardrobe_id: str | None = None
    garment_url: str | None = None
    category: GarmentCategory = GarmentCategory.UPPER_BODY


class TryOnResultRead(BaseModel):
    id: str
    profile_id: str
    garment_ref: str | None = None
    result_image_path: str | None = None
    result_image_b64: str | None = None
    size_recommendation: str | None = None
    fit_notes: list[str] = Field(default_factory=list)
    mix_match_suggestions: list[dict] = Field(default_factory=list)
    styling_narrative: str | None = None


# ── Size matching ───────────────────────────────────────────────


class SizeChartEntry(BaseModel):
    size_label: str
    chest_cm: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    inseam_cm: float | None = None
    shoulder_cm: float | None = None


class SizeMatchRequest(BaseModel):
    profile_id: str
    size_chart: list[SizeChartEntry]
    garment_category: GarmentCategory = GarmentCategory.UPPER_BODY


class SizeMatchResult(BaseModel):
    recommended_size: str
    confidence: float
    fit_notes: list[str] = Field(default_factory=list)
    diff_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)


class SizeHistoryEntry(BaseModel):
    id: str
    profile_id: str
    brand: str
    category: str | None = None
    size_bought: str | None = None
    size_fit: FitQuality | None = None
    notes: str | None = None
    created_at: str | None = None


class SizeHistoryCreate(BaseModel):
    brand: str
    category: str | None = None
    size_bought: str
    size_fit: FitQuality
    notes: str | None = None


# ── Mix-match ──────────────────────────────────────────────────


class MixMatchRequest(BaseModel):
    garment_image_b64: str | None = None
    garment_wardrobe_id: str | None = None
    garment_embedding: list[float] | None = None
    top_k: int = 5
    include_outfit_combos: bool = True


class MixMatchResult(BaseModel):
    item_id: str
    item_type: str | None = None
    description: str | None = None
    color: str | None = None
    similarity: float
    color_harmony: float
    overall_score: float
    image_path: str | None = None


class MixMatchResponse(BaseModel):
    query_item: str | None = None
    suggestions: list[MixMatchResult] = Field(default_factory=list)
    outfit_combinations: list[list[str]] = Field(default_factory=list)


# ── Outfit ────────────────────────────────────────────────────


class OutfitCreate(BaseModel):
    item_ids: list[str]
    occasion: str | None = None
    rating: int | None = None
    worn_date: str | None = None


class OutfitRead(BaseModel):
    id: str
    item_ids: list[str] = Field(default_factory=list)
    occasion: str | None = None
    rating: int | None = None
    worn_date: str | None = None
    created_at: str | None = None


# ── LLM Advisor ────────────────────────────────────────────────


class AdvisorRequest(BaseModel):
    prompt: str
    images_b64: list[str] = Field(default_factory=list)
    wardrobe_context: bool = True
    occasion: str | None = None
    stream: bool = False


class AdvisorResponse(BaseModel):
    advice: str
    model_used: str
    source: AdvisorSource
    outfit_ids: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    images_b64: list[str] = Field(default_factory=list)


class ConversationHistory(BaseModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── User feedback ──────────────────────────────────────────────


class OutfitFeedback(BaseModel):
    outfit_id: str
    liked: bool
    rating: int | None = None
    notes: str | None = None


class StylePreferenceUpdate(BaseModel):
    preferred_colors: list[str] | None = None
    preferred_styles: list[str] | None = None
    avoid_patterns: list[str] | None = None
    formality_preference: str | None = None


class StyleProfileRead(BaseModel):
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_styles: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    formality_preference: str | None = None
    brand_affinities: dict[str, float] = Field(default_factory=dict)
    size_corrections: dict[str, dict[str, str]] = Field(default_factory=dict)


# ── WebSocket messages ─────────────────────────────────────────


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ExtensionTryOnPayload(BaseModel):
    product_url: str
    product_images_b64: list[str] = Field(default_factory=list)
    product_title: str | None = None
    brand: str | None = None
    price: str | None = None
    size_chart_html: str | None = None
    source_site: str | None = None


class DetectedProduct(BaseModel):
    url: str
    title: str | None = None
    brand: str | None = None
    price: str | None = None
    images: list[str] = Field(default_factory=list)
    size_chart_html: str | None = None
    source_site: str | None = None
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Analytics ──────────────────────────────────────────────────


class WardrobeAnalytics(BaseModel):
    total_items: int = 0
    items_by_type: dict[str, int] = Field(default_factory=dict)
    items_by_color: dict[str, int] = Field(default_factory=dict)
    items_by_season: dict[str, int] = Field(default_factory=dict)
    most_worn: list[dict] = Field(default_factory=list)
    least_worn: list[dict] = Field(default_factory=list)
    total_value: float = 0.0
    avg_cost_per_wear: float = 0.0
    duplicate_groups: list[list[str]] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)


class MonthlyReport(BaseModel):
    month: str
    items_added: int = 0
    items_worn: int = 0
    outfits_created: int = 0
    top_outfits: list[dict] = Field(default_factory=list)
    underused_items: list[dict] = Field(default_factory=list)
    brand_size_corrections: dict[str, str] = Field(default_factory=dict)
    style_drift_score: float = 0.0
    cost_per_wear_avg: float = 0.0


# ── Knowledge base ─────────────────────────────────────────────


class KnowledgeEntry(BaseModel):
    title: str
    source: str
    url: str | None = None
    entry_type: Literal["paper", "model", "tool", "benchmark"]
    year: int | None = None
    venue: str | None = None
    relevance: str | None = None
    added_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlResult(BaseModel):
    source: str
    entries_found: int = 0
    entries_added: int = 0
    entries_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    crawl_time_seconds: float = 0.0
    crawled_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
