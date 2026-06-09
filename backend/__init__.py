"""Package initialization - expose key singletons."""
from backend.db.database import db
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
