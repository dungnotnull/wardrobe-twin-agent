/**
 * API client for wardrobe-twin-agent backend.
 * All requests go to localhost:7331 (FastAPI server).
 */
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:7331';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s for ML inference
  headers: { 'Content-Type': 'application/json' },
});

// ── Health ──────────────────────────────────────────────

export const healthCheck = () => api.get('/health');

// ── Body Profile ────────────────────────────────────────

export const scanBody = (data: {
  label?: string;
  measurements: Record<string, number | null>;
  webcam_frame_b64?: string;
}) => api.post('/scan', data);

export const listProfiles = () => api.get('/profiles');
export const getProfile = (id: string) => api.get(/profiles/);

// ── Wardrobe Catalog ────────────────────────────────────

export const addWardrobeItem = (data: {
  image_b64?: string;
  item_type?: string;
  color?: string;
  season?: string;
  brand?: string;
  size_label?: string;
}) => api.post('/catalog', data);

export const uploadWardrobePhoto = (formData: FormData) =>
  api.post('/catalog/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });

export const listWardrobeItems = (params?: {
  item_type?: string;
  color?: string;
  season?: string;
  limit?: number;
  offset?: number;
}) => api.get('/wardrobe', { params });

export const getWardrobeItem = (id: string) => api.get(/wardrobe/);
export const deleteWardrobeItem = (id: string) => api.delete(/wardrobe/);
export const searchWardrobeText = (query: string, top_k?: number) =>
  api.get('/wardrobe/search/text', { params: { query, top_k } });

// ── Virtual Try-On ──────────────────────────────────────

export const virtualTryOn = (data: {
  profile_id: string;
  garment_image_b64?: string;
  garment_wardrobe_id?: string;
  category?: string;
}) => api.post('/tryon', data);

// ── Size Matching ───────────────────────────────────────

export const sizeMatch = (data: {
  profile_id: string;
  size_chart: Array<{
    size_label: string;
    chest_cm?: number;
    waist_cm?: number;
    hip_cm?: number;
    inseam_cm?: number;
  }>;
  garment_category?: string;
}) => api.post('/size-match', data);

export const extractSizeChart = (data: {
  image_b64?: string;
  html?: string;
}) => api.post('/size-chart/extract', data);

// ── Mix-Match ───────────────────────────────────────────

export const mixMatch = (data: {
  garment_image_b64?: string;
  garment_wardrobe_id?: string;
  top_k?: number;
}) => api.post('/mix-match', data);

// ── LLM Advisor ─────────────────────────────────────────

export const askAdvisor = (data: {
  prompt: string;
  images_b64?: string[];
  wardrobe_context?: boolean;
  occasion?: string;
}) => api.post('/advisor', data);

// ── Data Management ─────────────────────────────────────

export const deleteAllData = () => api.delete('/data/all');

export default api;
