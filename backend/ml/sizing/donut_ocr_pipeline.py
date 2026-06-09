"""Donut OCR pipeline for size chart extraction.

Parses product page size charts (HTML tables or images) into structured
measurement data using the Donut document understanding transformer.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from PIL import Image

from config.settings import settings
from backend.core.models import SizeChartEntry

logger = logging.getLogger(__name__)


class DonutOCRPipeline:
    """Size chart OCR extraction using Donut or HTML regex fallback."""

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            from transformers import DonutProcessor, VisionEncoderDecoderModel
            import torch
            self._processor = DonutProcessor.from_pretrained(settings.DONUT_MODEL_ID)
            self._model = VisionEncoderDecoderModel.from_pretrained(settings.DONUT_MODEL_ID)
            self._model.to(settings.effective_device)
            self._model.eval()
            logger.info("Donut model loaded on %s", settings.effective_device)
        except Exception as e:
            logger.warning("Donut load failed: %s. Using HTML regex fallback.", e)
            self._model = None
            self._processor = None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def extract_size_chart(self, image: Image.Image | None = None, html: str | None = None) -> list[SizeChartEntry]:
        """Extract structured size chart from image or HTML."""
        self._ensure_loaded()
        if html:
            entries = self._extract_from_html(html)
            if entries:
                return entries
        if image is not None and self._model is not None and self._processor is not None:
            return self._extract_with_donut(image)
        if html:
            return self._extract_from_html(html)
        return []

    def _extract_with_donut(self, image: Image.Image) -> list[SizeChartEntry]:
        """Use Donut for OCR-based extraction from size chart image."""
        import torch
        task_prompt = "<s_cord-v2><s_table_predict>"
        inputs = self._processor(image, task_prompt, return_tensors="pt").to(settings.effective_device)
        with torch.no_grad():
            generated_ids = self._model.generate(**inputs, max_new_tokens=512)
        output_text = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return self._parse_donut_output(output_text)

    @staticmethod
    def _parse_donut_output(text: str) -> list[SizeChartEntry]:
        entries = []
        try:
            data = json.loads(text)
            rows = data if isinstance(data, list) else data.get("rows", [data])
            for row in rows:
                entries.append(SizeChartEntry(
                    size_label=str(row.get("size", row.get("size_label", ""))),
                    chest_cm=float(row.get("chest", row.get("chest_cm", 0)) or 0),
                    waist_cm=float(row.get("waist", row.get("waist_cm", 0)) or 0),
                    hip_cm=float(row.get("hip", row.get("hip_cm", 0)) or 0),
                    inseam_cm=float(row.get("inseam", row.get("inseam_cm", 0)) or 0),
                ))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("Failed to parse Donut output: %s", e)
        return entries

    @staticmethod
    def _extract_from_html(html: str) -> list[SizeChartEntry]:
        """Parse size chart from HTML table using regex patterns."""
        entries = []
        row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
        cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
        clean_tag = re.compile(r"<[^>]+>")

        rows = row_pattern.findall(html)
        if not rows:
            return entries

        header_cells = [clean_tag.sub("", c).strip().lower() for c in cell_pattern.findall(rows[0])]
        col_map: dict[str, int] = {}
        for i, h in enumerate(header_cells):
            if "size" in h:
                col_map["size"] = i
            elif "chest" in h or "bust" in h:
                col_map["chest"] = i
            elif "waist" in h:
                col_map["waist"] = i
            elif "hip" in h:
                col_map["hip"] = i
            elif "inseam" in h or "inside" in h:
                col_map["inseam"] = i
            elif "shoulder" in h:
                col_map["shoulder"] = i

        if not col_map:
            return entries

        for row_html in rows[1:]:
            cells = [clean_tag.sub("", c).strip() for c in cell_pattern.findall(row_html)]
            if len(cells) < 2:
                continue

            def get_val(key: str) -> float | None:
                idx = col_map.get(key)
                if idx is None or idx >= len(cells):
                    return None
                text = cells[idx].replace("cm", "").replace('"', "").replace("'", "").replace("\u2013", "-").strip()
                nums = re.findall(r"[\d.]+", text)
                return float(nums[0]) if nums else None

            size_label = cells[col_map.get("size", 0)].strip() if col_map.get("size", 0) is not None and col_map.get("size", 0) < len(cells) else ""
            if not size_label:
                continue

            entries.append(SizeChartEntry(
                size_label=size_label,
                chest_cm=get_val("chest"),
                waist_cm=get_val("waist"),
                hip_cm=get_val("hip"),
                inseam_cm=get_val("inseam"),
                shoulder_cm=get_val("shoulder"),
            ))

        return entries


donut_ocr = DonutOCRPipeline()
