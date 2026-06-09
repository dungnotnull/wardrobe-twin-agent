"""FastAPI application - main entry point for wardrobe-twin-agent backend.

All ML pipelines, database operations, and LLM advisor calls are exposed
through this server on localhost:7331.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from config.settings import settings
from backend.db.database import db
from backend.core.models import *
from backend.ml.body_scan.densepose_pipeline import body_scan
from backend.ml.garment_understanding.blip2_extractor import blip2_extractor
from backend.ml.garment_understanding.fashionclip_pipeline import fashionclip
from backend.ml.garment_understanding.garment_segmenter import garment_segmenter
from backend.ml.tryon.ootdiffusion_pipeline import ootd_pipeline
from backend.ml.sizing.donut_ocr_pipeline import donut_ocr
from backend.ml.sizing.size_matcher import size_matcher
from backend.core.wardrobe_catalog import wardrobe_catalog
from backend.core.mix_match_engine import mix_match
from backend.core.style_learning import style_learning
from backend.advisors.llm_advisor import llm_advisor
from backend.crawlers.knowledge_crawler import run_all_crawlers, schedule_crawls

logger = logging.getLogger(__name__)
_DEFAULT_PIN = "default"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    db.connect()
    schedule_crawls()
    logger.info("wardrobe-twin-agent API started on %s:%s", settings.HOST, settings.PORT)
    yield
    db.close()
    logger.info("wardrobe-twin-agent API stopped")


app = FastAPI(title="wardrobe-twin-agent", version="0.1.0", description="AI-powered virtual fitting room", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ═══ HEALTH ═══
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "device": settings.effective_device}


# ═══ BODY SCAN ═══
@app.post("/scan", response_model=BodyProfileRead)
async def scan_body(body: BodyProfileCreate):
    pin = _DEFAULT_PIN
    measurements = body.measurements
    if body.webcam_frame_b64:
        img_bytes = base64.b64decode(body.webcam_frame_b64)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        scan_result = body_scan.scan_from_image(pil_img)
        auto_meas = scan_result.get("measurements", {})
        for key in ["height_cm", "weight_kg", "chest_cm", "waist_cm", "hip_cm", "inseam_cm", "shoulder_cm"]:
            if getattr(measurements, key) is None and key in auto_meas:
                setattr(measurements, key, auto_meas[key])

    profile_data = {"label": body.label, "height_cm": measurements.height_cm, "weight_kg": measurements.weight_kg, "chest_cm": measurements.chest_cm, "waist_cm": measurements.waist_cm, "hip_cm": measurements.hip_cm, "inseam_cm": measurements.inseam_cm, "shoulder_cm": measurements.shoulder_cm}
    if body.webcam_frame_b64:
        profile_data["avatar_obj"] = scan_result.get("avatar_obj")
        profile_data["uv_map"] = scan_result.get("uv_map")

    profile_id = db.upsert_body_profile(profile_data, pin=pin)
    return BodyProfileRead(id=profile_id, label=body.label, measurements=measurements, has_avatar=profile_data.get("avatar_obj") is not None, has_uv_map=profile_data.get("uv_map") is not None)


@app.get("/profiles", response_model=list[BodyProfileRead])
async def list_profiles():
    return [BodyProfileRead(id=r["id"], label=r.get("label", "default"), measurements=BodyMeasurements(height_cm=r.get("height_cm"), weight_kg=r.get("weight_kg"), chest_cm=r.get("chest_cm"), waist_cm=r.get("waist_cm"), hip_cm=r.get("hip_cm"), inseam_cm=r.get("inseam_cm"), shoulder_cm=r.get("shoulder_cm")), has_avatar=r.get("avatar_obj_enc") is not None, has_uv_map=r.get("uv_map_enc") is not None, created_at=r.get("created_at"), updated_at=r.get("updated_at")) for r in db.list_body_profiles()]


@app.get("/profiles/{profile_id}", response_model=BodyProfileRead)
async def get_profile(profile_id: str):
    row = db.get_body_profile(profile_id, pin=_DEFAULT_PIN)
    if row is None:
        raise HTTPException(404, "Profile not found")
    return BodyProfileRead(id=row["id"], label=row.get("label", "default"), measurements=BodyMeasurements(height_cm=row.get("height_cm"), weight_kg=row.get("weight_kg"), chest_cm=row.get("chest_cm"), waist_cm=row.get("waist_cm"), hip_cm=row.get("hip_cm"), inseam_cm=row.get("inseam_cm"), shoulder_cm=row.get("shoulder_cm")), has_avatar=row.get("avatar_obj") is not None, has_uv_map=row.get("uv_map") is not None, created_at=row.get("created_at"), updated_at=row.get("updated_at"))


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    db.delete_body_profile(profile_id)
    return {"status": "deleted"}


# ═══ WARDROBE CATALOG ═══
@app.post("/catalog", response_model=WardrobeItemRead)
async def add_wardrobe_item(item: WardrobeItemCreate):
    return wardrobe_catalog.add_item(item, pin=_DEFAULT_PIN)


@app.post("/catalog/upload", response_model=WardrobeItemRead)
async def upload_wardrobe_photo(file: UploadFile = File(...), item_type: str | None = None, color: str | None = None, season: str | None = None, brand: str | None = None, size_label: str | None = None):
    image_bytes = await file.read()
    item = WardrobeItemCreate(item_type=item_type, color=color, season=season, brand=brand, size_label=size_label)
    return wardrobe_catalog.add_item(item, pin=_DEFAULT_PIN, image_bytes=image_bytes)


@app.post("/catalog/batch")
async def batch_upload(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        try:
            image_bytes = await file.read()
            item = WardrobeItemCreate()
            result = wardrobe_catalog.add_item(item, pin=_DEFAULT_PIN, image_bytes=image_bytes)
            results.append({"id": result.id, "status": "ok"})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "error": str(e)})
    return {"results": results}


@app.get("/wardrobe", response_model=list[WardrobeItemRead])
async def list_wardrobe(item_type: str | None = None, color: str | None = None, season: str | None = None, brand: str | None = None, limit: int = 100, offset: int = 0):
    return wardrobe_catalog.list_items(item_type=item_type, color=color, season=season, brand=brand, limit=limit, offset=offset)


@app.get("/wardrobe/{item_id}", response_model=WardrobeItemRead)
async def get_wardrobe_item(item_id: str):
    item = wardrobe_catalog.get_item(item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    return item


@app.patch("/wardrobe/{item_id}", response_model=WardrobeItemRead)
async def update_wardrobe_item(item_id: str, updates: WardrobeItemUpdate):
    result = wardrobe_catalog.update_item(item_id, updates)
    if result is None:
        raise HTTPException(404, "Item not found")
    return result


@app.delete("/wardrobe/{item_id}")
async def delete_wardrobe_item(item_id: str):
    if not wardrobe_catalog.delete_item(item_id):
        raise HTTPException(404, "Item not found")
    return {"status": "deleted"}


@app.get("/wardrobe/search/text")
async def search_wardrobe_text(query: str, top_k: int = 10):
    return wardrobe_catalog.search_by_text(query, top_k=top_k)


@app.get("/wardrobe/analytics")
async def wardrobe_analytics():
    return wardrobe_catalog.get_analytics()


# ═══ VIRTUAL TRY-ON ═══
@app.post("/tryon", response_model=TryOnResultRead)
async def virtual_tryon(request: TryOnRequest):
    pin = _DEFAULT_PIN
    profile = db.get_body_profile(request.profile_id, pin=pin)
    if profile is None:
        raise HTTPException(404, "Body profile not found")

    person_image = Image.new("RGB", (512, 768), (200, 200, 200))
    garment_image: Image.Image | None = None
    if request.garment_image_b64:
        img_bytes = base64.b64decode(request.garment_image_b64)
        garment_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    elif request.garment_wardrobe_id:
        item = db.get_wardrobe_item(request.garment_wardrobe_id, pin=pin)
        if item and item.get("image_path"):
            img_path = settings.WARDROBE_IMG_DIR / item["image_path"]
            if img_path.exists():
                garment_image = Image.open(str(img_path)).convert("RGB")
    if garment_image is None:
        raise HTTPException(400, "No garment image provided")

    # Segment garment background
    try:
        garment_segmented = garment_segmenter.remove_background(garment_image)
        garment_rgba = garment_segmented.convert("RGBA")
    except Exception:
        garment_rgba = garment_image

    result = ootd_pipeline.try_on(person_image=person_image, garment_image=garment_rgba, category=request.category.value if isinstance(request.category, GarmentCategory) else request.category)

    measurements = BodyMeasurements(height_cm=profile.get("height_cm"), chest_cm=profile.get("chest_cm"), waist_cm=profile.get("waist_cm"), hip_cm=profile.get("hip_cm"), inseam_cm=profile.get("inseam_cm"))
    size_rec = None
    fit_notes_list = []

    # Mix-match suggestions
    mm_request = MixMatchRequest(garment_image_b64=request.garment_image_b64, garment_wardrobe_id=request.garment_wardrobe_id, top_k=5)
    mm_result = mix_match.recommend(mm_request, pin=pin)

    # Styling narrative
    narrative = None
    try:
        narrative = await llm_advisor.generate_styling_narrative({"garment_ref": request.garment_wardrobe_id or "uploaded"}, request.profile_id)
    except Exception:
        pass

    result_img_bytes = None
    if result.get("result_image"):
        buf = io.BytesIO()
        result["result_image"].save(buf, format="PNG")
        result_img_bytes = buf.getvalue()

    tryon_id = db.insert_tryon_result({"profile_id": request.profile_id, "garment_ref": request.garment_wardrobe_id or request.garment_url or "uploaded", "result_image": result_img_bytes, "result_image_path": result.get("result_path"), "size_recommendation": size_rec, "fit_notes": json.dumps(fit_notes_list)}, pin=pin)

    result_b64 = base64.b64encode(result_img_bytes).decode("utf-8") if result_img_bytes else None

    return TryOnResultRead(id=tryon_id, profile_id=request.profile_id, garment_ref=request.garment_wardrobe_id or request.garment_url, result_image_path=result.get("result_path"), result_image_b64=result_b64, size_recommendation=size_rec, fit_notes=fit_notes_list, mix_match_suggestions=[s.model_dump() for s in mm_result.suggestions], styling_narrative=narrative)


# ═══ SIZE MATCHING ═══
@app.post("/size-match", response_model=SizeMatchResult)
async def size_match_endpoint(request: SizeMatchRequest):
    pin = _DEFAULT_PIN
    profile = db.get_body_profile(request.profile_id, pin=pin)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    measurements = BodyMeasurements(height_cm=profile.get("height_cm"), weight_kg=profile.get("weight_kg"), chest_cm=profile.get("chest_cm"), waist_cm=profile.get("waist_cm"), hip_cm=profile.get("hip_cm"), inseam_cm=profile.get("inseam_cm"), shoulder_cm=profile.get("shoulder_cm"))
    return size_matcher.match(measurements, request.size_chart, request.garment_category.value if isinstance(request.garment_category, GarmentCategory) else request.garment_category, brand=None, profile_id=request.profile_id)


@app.post("/size-chart/extract")
async def extract_size_chart(image_b64: str | None = None, html: str | None = None):
    image = None
    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    entries = donut_ocr.extract_size_chart(image=image, html=html)
    return {"entries": [e.model_dump() for e in entries]}


@app.post("/size-history")
async def add_size_history(profile_id: str, entry: SizeHistoryCreate):
    result = db.insert_size_history({"profile_id": profile_id, **entry.model_dump()})
    return {"id": result}


@app.get("/size-history/{profile_id}")
async def get_size_history(profile_id: str, brand: str | None = None):
    return db.get_size_history(profile_id, brand=brand)


# ═══ MIX-MATCH ═══
@app.post("/mix-match", response_model=MixMatchResponse)
async def mix_match_endpoint(request: MixMatchRequest):
    return mix_match.recommend(request, pin=_DEFAULT_PIN)


@app.post("/mix-match/complete-the-look")
async def complete_the_look(existing_item_ids: list[str], missing_slots: list[str] | None = None):
    return mix_match.complete_the_look(existing_item_ids, missing_slots)


# ═══ OUTFITS ═══
@app.post("/outfits")
async def create_outfit(outfit: OutfitCreate):
    outfit_id = db.insert_outfit_log({"item_ids": outfit.item_ids, "occasion": outfit.occasion, "rating": outfit.rating, "liked": None, "worn_date": outfit.worn_date})
    return {"id": outfit_id}


@app.get("/outfits")
async def list_outfits(limit: int = 50, offset: int = 0):
    return db.get_outfit_logs(limit=limit, offset=offset)


@app.post("/outfits/{outfit_id}/feedback")
async def outfit_feedback(outfit_id: str, liked: bool, rating: int | None = None):
    db.update_outfit_feedback(outfit_id, liked, rating)
    return {"status": "ok"}


# ═══ STYLE PROFILE ═══
@app.get("/style-profile/{profile_id}")
async def get_style_profile(profile_id: str):
    profile = db.get_style_profile(profile_id)
    if profile is None:
        return StyleProfileRead()
    return StyleProfileRead(**{k: profile.get(k, []) if isinstance(profile.get(k), list) else profile.get(k) for k in ["preferred_colors", "preferred_styles", "avoid_patterns", "formality_preference", "brand_affinities", "size_corrections"]})


@app.put("/style-profile/{profile_id}")
async def update_style_profile(profile_id: str, update: StylePreferenceUpdate):
    style_learning.update_style_from_preferences(profile_id, update)
    return {"status": "updated"}


# ═══ LLM ADVISOR ═══
@app.post("/advisor", response_model=AdvisorResponse)
async def advisor_endpoint(request: AdvisorRequest):
    return await llm_advisor.advise(request)


@app.post("/advisor/occasion")
async def occasion_outfits(occasion: str, profile_id: str, top_n: int = 3):
    outfits = await llm_advisor.generate_occasion_outfits(occasion, profile_id, top_n=top_n)
    return {"occasion": occasion, "outfits": outfits}


@app.post("/conversations")
async def create_conversation():
    session_id = db.create_conversation_session()
    return {"session_id": session_id}


@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    return db.get_conversation_session(session_id) or {"error": "Session not found"}


# ═══ MONTHLY REPORT ═══
@app.get("/report/{profile_id}")
async def monthly_report(profile_id: str, month: str | None = None):
    return style_learning.generate_monthly_report(profile_id, month).model_dump()


# ═══ KNOWLEDGE CRAWLER ═══
@app.post("/crawl")
async def trigger_crawl():
    results = await run_all_crawlers()
    return {"crawl_results": [r.model_dump() for r in results]}


# ═══ SEGMENTATION ═══
@app.post("/segment")
async def segment_garment(image_b64: str):
    img_bytes = base64.b64decode(image_b64)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    segmented = garment_segmenter.remove_background(pil_img)
    buf = io.BytesIO()
    segmented.save(buf, format="PNG")
    return {"segmented_b64": base64.b64encode(buf.getvalue()).decode("utf-8")}


# ═══ DATA MANAGEMENT ═══
@app.delete("/data/all")
async def delete_all_data():
    db.delete_all_data()
    return {"status": "all data deleted"}


# ═══ WEBSOCKET ═══
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("Extension WebSocket connected")
    try:
        while True:
            raw = await ws.receive_text()
            msg = WSMessage.model_validate_json(raw)
            if msg.type == "ping":
                await ws.send_json({"type": "pong", "request_id": msg.request_id})
            elif msg.type == "tryon_request":
                payload = ExtensionTryOnPayload(**msg.payload)
                result = await _handle_extension_tryon(payload)
                await ws.send_json({"type": "tryon_result", "payload": result, "request_id": msg.request_id})
            elif msg.type == "size_chart_extract":
                html = msg.payload.get("size_chart_html")
                result = donut_ocr.extract_size_chart(html=html)
                await ws.send_json({"type": "size_chart_result", "payload": {"entries": [e.model_dump() for e in result]}, "request_id": msg.request_id})
            elif msg.type == "mix_match_request":
                req = MixMatchRequest(**msg.payload)
                result = mix_match.recommend(req)
                await ws.send_json({"type": "mix_match_result", "payload": result.model_dump(), "request_id": msg.request_id})
            else:
                await ws.send_json({"type": "error", "payload": {"message": f"Unknown message type: {msg.type}"}, "request_id": msg.request_id})
    except WebSocketDisconnect:
        logger.info("Extension WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)


async def _handle_extension_tryon(payload: ExtensionTryOnPayload) -> dict:
    pin = _DEFAULT_PIN
    profiles = db.list_body_profiles()
    if not profiles:
        return {"error": "No body profile found. Please scan your body first."}
    profile_id = profiles[0]["id"]

    garment_image_b64 = payload.product_images_b64[0] if payload.product_images_b64 else None
    tryon_req = TryOnRequest(profile_id=profile_id, garment_image_b64=garment_image_b64, garment_url=payload.product_url)
    tryon_result = await virtual_tryon(tryon_req)

    size_result = None
    if payload.size_chart_html:
        size_chart = donut_ocr.extract_size_chart(html=payload.size_chart_html)
        if size_chart:
            profile = db.get_body_profile(profile_id, pin=pin)
            measurements = BodyMeasurements(height_cm=profile.get("height_cm"), chest_cm=profile.get("chest_cm"), waist_cm=profile.get("waist_cm"), hip_cm=profile.get("hip_cm"), inseam_cm=profile.get("inseam_cm"))
            size_result = size_matcher.match(measurements, size_chart).model_dump()

    mm_request = MixMatchRequest(garment_image_b64=garment_image_b64, top_k=5)
    mm_result = mix_match.recommend(mm_request, pin=pin)

    return {"tryon": tryon_result.model_dump(), "size_match": size_result, "mix_match": mm_result.model_dump(), "product": {"url": payload.product_url, "title": payload.product_title, "brand": payload.brand, "price": payload.price, "source_site": payload.source_site}}


# ═══ STATIC FILES ═══
from fastapi.staticfiles import StaticFiles
app.mount("/static/wardrobe", StaticFiles(directory=str(settings.WARDROBE_IMG_DIR), check_dir=False), name="wardrobe_images")
app.mount("/static/avatars", StaticFiles(directory=str(settings.AVATARS_DIR), check_dir=False), name="avatars")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings.ensure_dirs()
    uvicorn.run("backend.api.server:app", host=settings.HOST, port=settings.PORT, reload=True)


if __name__ == "__main__":
    main()
