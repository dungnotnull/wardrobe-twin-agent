"""SQLite database layer with AES-256-GCM encryption for body and wardrobe data.

Uses the cryptography library to encrypt/decrypt binary blobs stored
inside a regular SQLite database. The encryption key is derived from a
user-supplied PIN + device salt via PBKDF2-HMAC-SHA256.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Iterator

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from config.settings import settings

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 480_000
AES_KEY_SIZE = 32
AESGCM_NONCE_SIZE = 12
PBKDF2_SALT_SIZE = 16


def derive_key(pin: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from PIN + salt via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(pin.encode("utf-8"))


def generate_salt() -> bytes:
    """Generate a random 16-byte salt."""
    return os.urandom(PBKDF2_SALT_SIZE)


def encrypt_blob(plaintext: bytes, pin: str, salt: bytes | None = None) -> dict[str, bytes]:
    """AES-256-GCM encrypt plaintext. Returns {ciphertext, nonce, salt}."""
    if salt is None:
        salt = generate_salt()
    key = derive_key(pin, salt)
    nonce = os.urandom(AESGCM_NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return {"ciphertext": ciphertext, "nonce": nonce, "salt": salt}


def decrypt_blob(ciphertext: bytes, nonce: bytes, salt: bytes, pin: str) -> bytes:
    """AES-256-GCM decrypt."""
    key = derive_key(pin, salt)
    return AESGCM(key).decrypt(nonce, ciphertext, None)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS body_profiles (
    id              TEXT PRIMARY KEY,
    label           TEXT NOT NULL DEFAULT 'default',
    height_cm       REAL,
    weight_kg       REAL,
    chest_cm        REAL,
    waist_cm        REAL,
    hip_cm          REAL,
    inseam_cm       REAL,
    shoulder_cm     REAL,
    avatar_obj_enc  BLOB,
    avatar_obj_nonce BLOB,
    avatar_obj_salt  BLOB,
    uv_map_enc      BLOB,
    uv_map_nonce    BLOB,
    uv_map_salt     BLOB,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wardrobe_items (
    id              TEXT PRIMARY KEY,
    image_path      TEXT NOT NULL,
    image_enc       BLOB,
    image_nonce     BLOB,
    image_salt      BLOB,
    description     TEXT,
    tags            TEXT,
    item_type       TEXT,
    color           TEXT,
    pattern         TEXT,
    style           TEXT,
    material        TEXT,
    season          TEXT DEFAULT 'all',
    embedding       BLOB,
    brand           TEXT,
    size_label      TEXT,
    purchase_date   TEXT,
    purchase_price  REAL,
    worn_count      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS size_history (
    id              TEXT PRIMARY KEY,
    profile_id      TEXT NOT NULL REFERENCES body_profiles(id),
    brand           TEXT NOT NULL,
    category        TEXT,
    size_bought     TEXT,
    size_fit        TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outfit_logs (
    id              TEXT PRIMARY KEY,
    item_ids        TEXT NOT NULL,
    occasion        TEXT,
    rating          INTEGER,
    liked           INTEGER,
    worn_date       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tryon_results (
    id              TEXT PRIMARY KEY,
    profile_id      TEXT NOT NULL REFERENCES body_profiles(id),
    garment_ref     TEXT,
    result_image_enc BLOB,
    result_image_nonce BLOB,
    result_image_salt BLOB,
    result_image_path TEXT,
    size_recommendation TEXT,
    fit_notes       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS style_profiles (
    id              TEXT PRIMARY KEY,
    profile_id      TEXT NOT NULL REFERENCES body_profiles(id),
    preferred_colors TEXT,
    preferred_styles TEXT,
    avoid_patterns  TEXT,
    formality_preference TEXT,
    brand_affinities TEXT,
    size_corrections TEXT,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id              TEXT PRIMARY KEY,
    messages        TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,
    url             TEXT,
    entry_type      TEXT NOT NULL,
    year            INTEGER,
    venue           TEXT,
    relevance       TEXT,
    added_date      TEXT NOT NULL,
    metadata        TEXT,
    UNIQUE(title, source)
);

CREATE TABLE IF NOT EXISTS crawl_logs (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    entries_found   INTEGER DEFAULT 0,
    entries_added   INTEGER DEFAULT 0,
    entries_skipped INTEGER DEFAULT 0,
    errors          TEXT,
    crawl_time_seconds REAL,
    crawled_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS result_cache (
    cache_key       TEXT PRIMARY KEY,
    result_data     BLOB NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_wardrobe_type ON wardrobe_items(item_type);
CREATE INDEX IF NOT EXISTS idx_wardrobe_color ON wardrobe_items(color);
CREATE INDEX IF NOT EXISTS idx_wardrobe_season ON wardrobe_items(season);
CREATE INDEX IF NOT EXISTS idx_wardrobe_brand ON wardrobe_items(brand);
CREATE INDEX IF NOT EXISTS idx_size_history_brand ON size_history(brand);
CREATE INDEX IF NOT EXISTS idx_outfit_rating ON outfit_logs(rating);
CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_result_cache_age ON result_cache(created_at);
"""


class Database:
    """Encrypted SQLite database manager."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.DB_PATH
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        settings.ensure_dirs()
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.connect()
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def commit(self) -> None:
        self.conn.commit()

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    # ── Body profile ─────────────────────────────────────────────

    def upsert_body_profile(self, profile: dict, pin: str) -> str:
        profile_id = profile.get("id") or self._new_id()
        avatar_enc = encrypt_blob(profile["avatar_obj"], pin) if profile.get("avatar_obj") else {"ciphertext": None, "nonce": None, "salt": None}
        uv_enc = encrypt_blob(profile["uv_map"], pin) if profile.get("uv_map") else {"ciphertext": None, "nonce": None, "salt": None}

        self.conn.execute(
            """INSERT INTO body_profiles
                (id, label, height_cm, weight_kg, chest_cm, waist_cm, hip_cm,
                 inseam_cm, shoulder_cm, avatar_obj_enc, avatar_obj_nonce,
                 avatar_obj_salt, uv_map_enc, uv_map_nonce, uv_map_salt)
            VALUES (:id, :label, :height_cm, :weight_kg, :chest_cm, :waist_cm, :hip_cm,
                    :inseam_cm, :shoulder_cm, :avatar_obj_enc, :avatar_obj_nonce,
                    :avatar_obj_salt, :uv_map_enc, :uv_map_nonce, :uv_map_salt)
            ON CONFLICT(id) DO UPDATE SET
                label=excluded.label, height_cm=excluded.height_cm,
                weight_kg=excluded.weight_kg, chest_cm=excluded.chest_cm,
                waist_cm=excluded.waist_cm, hip_cm=excluded.hip_cm,
                inseam_cm=excluded.inseam_cm, shoulder_cm=excluded.shoulder_cm,
                avatar_obj_enc=excluded.avatar_obj_enc,
                avatar_obj_nonce=excluded.avatar_obj_nonce,
                avatar_obj_salt=excluded.avatar_obj_salt,
                uv_map_enc=excluded.uv_map_enc,
                uv_map_nonce=excluded.uv_map_nonce,
                uv_map_salt=excluded.uv_map_salt,
                updated_at=datetime('now')""",
            {
                "id": profile_id, "label": profile.get("label", "default"),
                "height_cm": profile.get("height_cm"), "weight_kg": profile.get("weight_kg"),
                "chest_cm": profile.get("chest_cm"), "waist_cm": profile.get("waist_cm"),
                "hip_cm": profile.get("hip_cm"), "inseam_cm": profile.get("inseam_cm"),
                "shoulder_cm": profile.get("shoulder_cm"),
                "avatar_obj_enc": avatar_enc["ciphertext"], "avatar_obj_nonce": avatar_enc["nonce"],
                "avatar_obj_salt": avatar_enc["salt"],
                "uv_map_enc": uv_enc["ciphertext"], "uv_map_nonce": uv_enc["nonce"],
                "uv_map_salt": uv_enc["salt"],
            },
        )
        self.commit()
        return profile_id

    def get_body_profile(self, profile_id: str, pin: str | None = None) -> dict | None:
        row = self.conn.execute("SELECT * FROM body_profiles WHERE id = ?", (profile_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        if pin:
            for prefix in ("avatar_obj", "uv_map"):
                enc_key, nonce_key, salt_key = f"{prefix}_enc", f"{prefix}_nonce", f"{prefix}_salt"
                if result.get(enc_key):
                    try:
                        result[prefix] = decrypt_blob(result[enc_key], result[nonce_key], result[salt_key], pin)
                    except Exception:
                        result[prefix] = None
        return result

    def list_body_profiles(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, label, height_cm, weight_kg, chest_cm, waist_cm, hip_cm, inseam_cm, shoulder_cm, created_at, updated_at FROM body_profiles"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_body_profile(self, profile_id: str) -> bool:
        self.conn.execute("DELETE FROM body_profiles WHERE id = ?", (profile_id,))
        self.conn.execute("DELETE FROM size_history WHERE profile_id = ?", (profile_id,))
        self.conn.execute("DELETE FROM style_profiles WHERE profile_id = ?", (profile_id,))
        self.commit()
        return True

    # ── Wardrobe items ────────────────────────────────────────────

    def insert_wardrobe_item(self, item: dict, pin: str) -> str:
        item_id = item.get("id") or self._new_id()
        img_enc = encrypt_blob(item["image_blob"], pin) if item.get("image_blob") else {"ciphertext": None, "nonce": None, "salt": None}

        self.conn.execute(
            """INSERT INTO wardrobe_items
                (id, image_path, image_enc, image_nonce, image_salt,
                 description, tags, item_type, color, pattern, style, material, season,
                 embedding, brand, size_label, purchase_date, purchase_price)
            VALUES (:id, :image_path, :image_enc, :image_nonce, :image_salt,
                    :description, :tags, :item_type, :color, :pattern, :style, :material, :season,
                    :embedding, :brand, :size_label, :purchase_date, :purchase_price)""",
            {
                "id": item_id, "image_path": item.get("image_path", ""),
                "image_enc": img_enc["ciphertext"], "image_nonce": img_enc["nonce"], "image_salt": img_enc["salt"],
                "description": item.get("description"), "tags": item.get("tags"),
                "item_type": item.get("item_type"), "color": item.get("color"),
                "pattern": item.get("pattern"), "style": item.get("style"), "material": item.get("material"),
                "season": item.get("season", "all"), "embedding": item.get("embedding"),
                "brand": item.get("brand"), "size_label": item.get("size_label"),
                "purchase_date": item.get("purchase_date"), "purchase_price": item.get("purchase_price"),
            },
        )
        self.commit()
        return item_id

    def update_wardrobe_item(self, item_id: str, updates: dict) -> bool:
        sets = []
        params: list[Any] = []
        for key in ("description", "tags", "item_type", "color", "pattern", "style", "material", "season", "brand", "size_label"):
            if key in updates and updates[key] is not None:
                sets.append(f"{key} = ?")
                params.append(updates[key])
        if not sets:
            return False
        sets.append("updated_at = datetime('now')")
        params.append(item_id)
        self.conn.execute(f"UPDATE wardrobe_items SET {', '.join(sets)} WHERE id = ?", params)
        self.commit()
        return True

    def get_wardrobe_item(self, item_id: str, pin: str | None = None) -> dict | None:
        row = self.conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        if pin and result.get("image_enc"):
            try:
                result["image_blob"] = decrypt_blob(result["image_enc"], result["image_nonce"], result["image_salt"], pin)
            except Exception:
                result["image_blob"] = None
        return result

    def list_wardrobe_items(self, item_type: str | None = None, color: str | None = None, season: str | None = None, brand: str | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        clauses, params = [], []
        if item_type:
            clauses.append("item_type = ?"), params.append(item_type)
        if color:
            clauses.append("color = ?"), params.append(color)
        if season:
            clauses.append("season = ?"), params.append(season)
        if brand:
            clauses.append("brand = ?"), params.append(brand)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.extend([limit, offset])
        rows = self.conn.execute(
            f"""SELECT id, image_path, description, tags, item_type, color, pattern, style, material, season,
                        brand, size_label, purchase_price, worn_count, created_at
                FROM wardrobe_items{where} ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def increment_worn_count(self, item_id: str) -> None:
        self.conn.execute("UPDATE wardrobe_items SET worn_count = worn_count + 1, updated_at = datetime('now') WHERE id = ?", (item_id,))
        self.commit()

    def delete_wardrobe_item(self, item_id: str) -> bool:
        row = self.conn.execute("SELECT image_path FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return False
        img_path = settings.WARDROBE_IMG_DIR / row["image_path"]
        if img_path.exists():
            img_path.unlink()
        self.conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
        self.commit()
        return True

    def count_wardrobe_items(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM wardrobe_items").fetchone()
        return row["cnt"] if row else 0

    def search_wardrobe_by_embedding(self, query_embedding: bytes, top_k: int = 10) -> list[dict]:
        import numpy as np
        query_vec = np.frombuffer(query_embedding, dtype=np.float32)
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        rows = self.conn.execute("SELECT id, embedding, description, tags, item_type, color, season, image_path FROM wardrobe_items WHERE embedding IS NOT NULL").fetchall()
        scores = []
        for r in rows:
            emb = np.frombuffer(r["embedding"], dtype=np.float32)
            emb_norm = emb / (np.linalg.norm(emb) + 1e-8)
            sim = float(np.dot(query_norm, emb_norm))
            scores.append((sim, dict(r)))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [{**item, "similarity": round(score, 4)} for score, item in scores[:top_k]]

    def get_all_embeddings(self) -> list[tuple[str, Any]]:
        rows = self.conn.execute("SELECT id, embedding FROM wardrobe_items WHERE embedding IS NOT NULL").fetchall()
        return [(r["id"], r["embedding"]) for r in rows]

    # ── Size history ─────────────────────────────────────────────

    def insert_size_history(self, entry: dict) -> str:
        entry_id = entry.get("id") or self._new_id()
        self.conn.execute(
            "INSERT INTO size_history (id, profile_id, brand, category, size_bought, size_fit, notes) VALUES (:id, :profile_id, :brand, :category, :size_bought, :size_fit, :notes)",
            {"id": entry_id, "profile_id": entry.get("profile_id", ""), "brand": entry["brand"], "category": entry.get("category"), "size_bought": entry.get("size_bought"), "size_fit": entry.get("size_fit"), "notes": entry.get("notes")},
        )
        self.commit()
        return entry_id

    def get_size_history(self, profile_id: str, brand: str | None = None) -> list[dict]:
        if brand:
            rows = self.conn.execute("SELECT * FROM size_history WHERE profile_id = ? AND brand = ? ORDER BY created_at DESC", (profile_id, brand)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM size_history WHERE profile_id = ? ORDER BY created_at DESC", (profile_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_brand_size_corrections(self, profile_id: str) -> dict[str, dict[str, str]]:
        rows = self.conn.execute("SELECT brand, category, size_bought, size_fit FROM size_history WHERE profile_id = ? AND size_fit IS NOT NULL", (profile_id,)).fetchall()
        corrections: dict[str, dict[str, str]] = {}
        for r in rows:
            brand = r["brand"]
            if brand not in corrections:
                corrections[brand] = {}
            key = r["category"] or "default"
            fit = r["size_fit"]
            if fit in ("tight", "loose"):
                corrections[brand][key] = fit
        return corrections

    # ── Outfit logs ───────────────────────────────────────────────

    def insert_outfit_log(self, outfit: dict) -> str:
        outfit_id = outfit.get("id") or self._new_id()
        self.conn.execute(
            "INSERT INTO outfit_logs (id, item_ids, occasion, rating, liked, worn_date) VALUES (:id, :item_ids, :occasion, :rating, :liked, :worn_date)",
            {"id": outfit_id, "item_ids": json.dumps(outfit.get("item_ids", [])), "occasion": outfit.get("occasion"), "rating": outfit.get("rating"), "liked": outfit.get("liked"), "worn_date": outfit.get("worn_date")},
        )
        self.commit()
        for item_id in outfit.get("item_ids", []):
            self.increment_worn_count(item_id)
        return outfit_id

    def get_outfit_logs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM outfit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["item_ids"] = json.loads(d.get("item_ids", "[]"))
            results.append(d)
        return results

    def update_outfit_feedback(self, outfit_id: str, liked: bool, rating: int | None = None) -> bool:
        self.conn.execute("UPDATE outfit_logs SET liked = ?, rating = COALESCE(?, rating) WHERE id = ?", (1 if liked else 0, rating, outfit_id))
        self.commit()
        return True

    # ── Try-on results ────────────────────────────────────────────

    def insert_tryon_result(self, result: dict, pin: str) -> str:
        result_id = result.get("id") or self._new_id()
        img_enc = encrypt_blob(result["result_image"], pin) if result.get("result_image") else {"ciphertext": None, "nonce": None, "salt": None}
        self.conn.execute(
            """INSERT INTO tryon_results
                (id, profile_id, garment_ref, result_image_enc, result_image_nonce,
                 result_image_salt, result_image_path, size_recommendation, fit_notes)
            VALUES (:id, :profile_id, :garment_ref, :result_image_enc, :result_image_nonce,
                    :result_image_salt, :result_image_path, :size_recommendation, :fit_notes)""",
            {
                "id": result_id, "profile_id": result["profile_id"],
                "garment_ref": result.get("garment_ref"),
                "result_image_enc": img_enc["ciphertext"], "result_image_nonce": img_enc["nonce"], "result_image_salt": img_enc["salt"],
                "result_image_path": result.get("result_image_path"),
                "size_recommendation": result.get("size_recommendation"),
                "fit_notes": json.dumps(result.get("fit_notes", [])) if isinstance(result.get("fit_notes"), list) else result.get("fit_notes"),
            },
        )
        self.commit()
        return result_id

    # ── Style profiles ────────────────────────────────────────────

    def upsert_style_profile(self, profile_id: str, data: dict) -> str:
        sp_id = self._new_id()
        existing = self.conn.execute("SELECT id FROM style_profiles WHERE profile_id = ?", (profile_id,)).fetchone()
        if existing:
            sp_id = existing["id"]
            self.conn.execute(
                """UPDATE style_profiles SET preferred_colors=?, preferred_styles=?, avoid_patterns=?,
                    formality_preference=?, brand_affinities=?, size_corrections=?, updated_at=datetime('now') WHERE id=?""",
                (json.dumps(data.get("preferred_colors", [])), json.dumps(data.get("preferred_styles", [])),
                 json.dumps(data.get("avoid_patterns", [])), data.get("formality_preference"),
                 json.dumps(data.get("brand_affinities", {})), json.dumps(data.get("size_corrections", {})), sp_id),
            )
        else:
            self.conn.execute(
                """INSERT INTO style_profiles (id, profile_id, preferred_colors, preferred_styles, avoid_patterns,
                    formality_preference, brand_affinities, size_corrections)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sp_id, profile_id, json.dumps(data.get("preferred_colors", [])), json.dumps(data.get("preferred_styles", [])),
                 json.dumps(data.get("avoid_patterns", [])), data.get("formality_preference"),
                 json.dumps(data.get("brand_affinities", {})), json.dumps(data.get("size_corrections", {}))),
            )
        self.commit()
        return sp_id

    def get_style_profile(self, profile_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM style_profiles WHERE profile_id = ?", (profile_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        for key in ("preferred_colors", "preferred_styles", "avoid_patterns", "brand_affinities", "size_corrections"):
            if result.get(key):
                result[key] = json.loads(result[key])
        return result

    # ── Conversation sessions ─────────────────────────────────────

    def create_conversation_session(self) -> str:
        session_id = self._new_id()
        self.conn.execute("INSERT INTO conversation_sessions (id, messages) VALUES (?, '[]')", (session_id,))
        self.commit()
        return session_id

    def get_conversation_session(self, session_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["messages"] = json.loads(result.get("messages", "[]"))
        return result

    def append_conversation_message(self, session_id: str, message: dict) -> None:
        session = self.get_conversation_session(session_id)
        if session is None:
            return
        messages = session["messages"]
        messages.append(message)
        self.conn.execute("UPDATE conversation_sessions SET messages = ?, updated_at = datetime('now') WHERE id = ?", (json.dumps(messages), session_id))
        self.commit()

    def list_conversation_sessions(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute("SELECT id, created_at, updated_at FROM conversation_sessions ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ── Knowledge entries ─────────────────────────────────────────

    def insert_knowledge_entry(self, entry: dict) -> str | None:
        entry_id = entry.get("id") or self._new_id()
        try:
            self.conn.execute(
                """INSERT INTO knowledge_entries (id, title, source, url, entry_type, year, venue, relevance, added_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, entry["title"], entry["source"], entry.get("url"), entry["entry_type"],
                 entry.get("year"), entry.get("venue"), entry.get("relevance"), entry.get("added_date"), json.dumps(entry.get("metadata", {}))),
            )
            self.commit()
            return entry_id
        except sqlite3.IntegrityError:
            return None

    def knowledge_entry_exists(self, title: str, source: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM knowledge_entries WHERE title = ? AND source = ?", (title, source)).fetchone()
        return row is not None

    def insert_crawl_log(self, log: dict) -> str:
        log_id = self._new_id()
        self.conn.execute(
            "INSERT INTO crawl_logs (id, source, entries_found, entries_added, entries_skipped, errors, crawl_time_seconds) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (log_id, log["source"], log.get("entries_found", 0), log.get("entries_added", 0), log.get("entries_skipped", 0),
             json.dumps(log.get("errors", [])), log.get("crawl_time_seconds", 0.0)),
        )
        self.commit()
        return log_id

    # ── Result cache ─────────────────────────────────────────────

    def get_cached_result(self, cache_key: str) -> bytes | None:
        row = self.conn.execute("SELECT result_data FROM result_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        return row["result_data"] if row else None

    def set_cached_result(self, cache_key: str, data: bytes) -> None:
        self.conn.execute("INSERT OR REPLACE INTO result_cache (cache_key, result_data, created_at) VALUES (?, ?, datetime('now'))", (cache_key, data))
        self.commit()

    def purge_expired_cache(self, max_age_hours: int = 24) -> int:
        cursor = self.conn.execute("DELETE FROM result_cache WHERE created_at < datetime('now', ?)", (f"-{max_age_hours} hours",))
        self.commit()
        return cursor.rowcount

    # ── Nuclear delete ────────────────────────────────────────────

    def delete_all_data(self) -> None:
        self.close()
        if self.db_path.exists():
            self.db_path.unlink()
        for f in settings.AVATARS_DIR.glob("*"):
            if f.is_file():
                f.unlink()
        for f in settings.WARDROBE_IMG_DIR.glob("*"):
            if f.is_file() and f.name != ".gitkeep":
                f.unlink()
        for f in settings.CACHE_DIR.glob("*"):
            if f.is_file():
                f.unlink()


db = Database()
