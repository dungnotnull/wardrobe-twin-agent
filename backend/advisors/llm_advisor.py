"""LLM Advisor layer with pluggable fallback chain.

Chain: Claude API -> GPT-4V -> Ollama (local).
Each advisor is tried in order; if one fails, the next is attempted.
Supports streaming responses, conversation history, and wardrobe context.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from config.settings import settings
from backend.core.models import AdvisorRequest, AdvisorResponse, AdvisorSource, ChatMessage, ConversationHistory
from backend.db.database import db

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_BASE = (
    "You are a professional wardrobe stylist and fashion advisor for the Wardrobe Twin Agent app. "
    "You help users choose outfits, suggest mix-match combinations, provide sizing and fit guidance, "
    "and offer style coaching. Be concise, specific, and practical. "
    "When suggesting outfits, reference specific items from the user's wardrobe by type and color. "
    "Always consider the occasion the user mentions. "
    "If the user asks about sizing, compare their measurements to typical size charts."
)


class BaseAdvisor(ABC):
    @abstractmethod
    async def call(self, prompt: str, images_b64: list[str] | None = None, context: str = "") -> str: ...

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def source(self) -> AdvisorSource: ...


class ClaudeAdvisor(BaseAdvisor):
    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True
        if not settings.ANTHROPIC_API_KEY:
            return False
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            return True
        except Exception as e:
            logger.warning("Claude client init failed: %s", e)
            return False

    async def call(self, prompt: str, images_b64: list[str] | None = None, context: str = "") -> str:
        if not self._ensure_client():
            raise RuntimeError("Claude API key not configured")

        system_prompt = SYSTEM_PROMPT_BASE
        if context:
            system_prompt += f"\n\nUser wardrobe context:\n{context}"

        content_blocks = []
        if images_b64:
            for img_b64 in images_b64:
                media_type = "image/png" if "PNG" in img_b64[:50] else "image/jpeg"
                content_blocks.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}})
        content_blocks.append({"type": "text", "text": prompt})

        response = self._client.messages.create(
            model=settings.CLAUDE_MODEL, max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
        return response.content[0].text

    def name(self) -> str:
        return settings.CLAUDE_MODEL

    def source(self) -> AdvisorSource:
        return AdvisorSource.CLAUDE


class GPT4VAdvisor(BaseAdvisor):
    def __init__(self) -> None:
        self._client = None

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True
        if not settings.OPENAI_API_KEY:
            return False
        try:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            return True
        except Exception as e:
            logger.warning("OpenAI client init failed: %s", e)
            return False

    async def call(self, prompt: str, images_b64: list[str] | None = None, context: str = "") -> str:
        if not self._ensure_client():
            raise RuntimeError("OpenAI API key not configured")

        system_msg = SYSTEM_PROMPT_BASE
        if context:
            system_msg += f"\n\nUser wardrobe context:\n{context}"

        messages = [{"role": "system", "content": system_msg}]
        if images_b64:
            content = []
            for img_b64 in images_b64:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
            content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(model=settings.GPT4V_MODEL, messages=messages, max_tokens=1024)
        return response.choices[0].message.content or ""

    def name(self) -> str:
        return settings.GPT4V_MODEL

    def source(self) -> AdvisorSource:
        return AdvisorSource.OPENAI


class OllamaAdvisor(BaseAdvisor):
    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_HOST

    async def call(self, prompt: str, images_b64: list[str] | None = None, context: str = "") -> str:
        import aiohttp
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        payload = {
            "model": settings.OLLAMA_MODEL, "prompt": full_prompt,
            "system": SYSTEM_PROMPT_BASE, "stream": False,
            "options": {"num_predict": 512},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self._base_url}/api/generate", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama returned status {resp.status}")
                data = await resp.json()
                return data.get("response", "")

    def name(self) -> str:
        return settings.OLLAMA_MODEL

    def source(self) -> AdvisorSource:
        return AdvisorSource.OLLAMA


class LLMAdvisor:
    """Orchestrates the fallback chain: Claude -> GPT-4V -> Ollama."""

    def __init__(self) -> None:
        self.chain: list[BaseAdvisor] = [ClaudeAdvisor(), GPT4VAdvisor(), OllamaAdvisor()]

    async def advise(self, request: AdvisorRequest, session_id: str | None = None) -> AdvisorResponse:
        """Try each advisor in the fallback chain until one succeeds."""
        images = request.images_b64 or []
        context = self._build_wardrobe_context() if request.wardrobe_context else ""

        if request.occasion:
            context += f"\nOccasion: {request.occasion}"

        last_error = ""
        for advisor in self.chain:
            try:
                result = await advisor.call(prompt=request.prompt, images_b64=images, context=context)
                response = AdvisorResponse(advice=result, model_used=advisor.name(), source=advisor.source())

                if session_id:
                    self._save_message(session_id, "user", request.prompt, images)
                    self._save_message(session_id, "assistant", result)

                return response
            except Exception as e:
                logger.info("%s failed: %s, trying next", advisor.name(), e)
                last_error = str(e)
                continue

        return AdvisorResponse(
            advice=f"Styling advisor unavailable. Last error: {last_error}",
            model_used="none", source=AdvisorSource.FALLBACK,
        )

    async def generate_styling_narrative(self, tryon_data: dict, profile_id: str) -> str:
        """Generate a styling narrative for a try-on result."""
        garment_desc = tryon_data.get("garment_ref", "the garment")
        size_rec = tryon_data.get("size_recommendation", "")
        fit_notes = tryon_data.get("fit_notes", [])

        prompt_parts = [
            f"Generate a brief styling narrative (2-3 sentences) for a virtual try-on result.",
            f"Garment: {garment_desc}.",
        ]
        if size_rec:
            prompt_parts.append(f"Recommended size: {size_rec}.")
        if fit_notes:
            prompt_parts.append(f"Fit notes: {', '.join(fit_notes)}")
        prompt_parts.append("Include one mix-match suggestion from the user's wardrobe.")

        request = AdvisorRequest(prompt=" ".join(prompt_parts), wardrobe_context=True)
        response = await self.advise(request)
        return response.advice

    async def generate_occasion_outfits(self, occasion: str, profile_id: str, top_n: int = 3) -> list[dict]:
        """Generate complete outfit suggestions for a specific occasion."""
        from backend.core.wardrobe_catalog import wardrobe_catalog
        from backend.core.mix_match_engine import mix_match, TYPE_SLOTS

        items = wardrobe_catalog.list_items(limit=200)
        if not items:
            return []

        # Group items by type slot
        by_slot: dict[str, list[dict]] = defaultdict(list)
        for item in items:
            slot = mix_match._classify_type(item.item_type or "")
            if slot:
                by_slot[slot].append(item)

        # Build outfits from available slots
        outfits = []
        tops = by_slot.get("top", []) + by_slot.get("outerwear", [])
        bottoms = by_slot.get("bottom", [])
        dresses = by_slot.get("dress", [])
        shoes = by_slot.get("shoes", [])

        if dresses:
            for d in dresses[:top_n]:
                outfit = {"items": [d], "occasion": occasion}
                if shoes:
                    outfit["items"].append(shoes[0])
                outfits.append(outfit)
        elif tops and bottoms:
            for i, (t, b) in enumerate(zip(tops, bottoms)):
                if i >= top_n:
                    break
                outfit = {"items": [t, b], "occasion": occasion}
                if shoes:
                    outfit["items"].append(shoes[0])
                outfits.append(outfit)

        # Get LLM narrative for each outfit
        for outfit in outfits:
            item_descs = [f"{i.item_type} ({i.color})" for i in outfit["items"] if hasattr(i, "item_type")]
            prompt = f"Suggest a brief styling tip for wearing {' + '.join(item_descs)} for a {occasion}. One sentence."
            try:
                req = AdvisorRequest(prompt=prompt, occasion=occasion, wardrobe_context=True)
                resp = await self.advise(req)
                outfit["narrative"] = resp.advice
            except Exception:
                outfit["narrative"] = ""
            outfit["item_ids"] = [i.id for i in outfit["items"] if hasattr(i, "id")]

        return outfits[:top_n]

    @staticmethod
    def _build_wardrobe_context() -> str:
        try:
            items = db.list_wardrobe_items(limit=50)
        except Exception:
            return ""

        if not items:
            return "Wardrobe is empty."

        from collections import Counter
        type_counts: dict[str, int] = Counter(r.get("item_type", "unknown") for r in items)
        colors = [r.get("color", "") for r in items if r.get("color")]

        summary = "Wardrobe summary:\n"
        for t, count in sorted(type_counts.items()):
            summary += f"  - {count}x {t}\n"
        if colors:
            top_colors = Counter(colors).most_common(5)
            summary += f"  Dominant colors: {', '.join(c for c, _ in top_colors)}\n"
        return summary

    @staticmethod
    def _save_message(session_id: str, role: str, content: str, images: list[str] | None = None) -> None:
        message = {"role": role, "content": content, "timestamp": __import__("datetime").datetime.utcnow().isoformat()}
        if images:
            message["images_b64"] = images[:3]
        try:
            db.append_conversation_message(session_id, message)
        except Exception:
            pass


from collections import defaultdict

llm_advisor = LLMAdvisor()
