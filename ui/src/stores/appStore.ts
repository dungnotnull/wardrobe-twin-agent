/**
 * Zustand store for global app state.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface BodyMeasurements {
  height_cm: number | null;
  weight_kg: number | null;
  chest_cm: number | null;
  waist_cm: number | null;
  hip_cm: number | null;
  inseam_cm: number | null;
  shoulder_cm: number | null;
}

export interface BodyProfile {
  id: string;
  label: string;
  measurements: BodyMeasurements;
  has_avatar: boolean;
  has_uv_map: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface WardrobeItem {
  id: string;
  image_path: string | null;
  description: string | null;
  tags: string[];
  item_type: string | null;
  color: string | null;
  season: string | null;
  brand: string | null;
  size_label: string | null;
  worn_count: number;
  created_at: string | null;
}

export interface TryOnResult {
  id: string;
  profile_id: string;
  garment_ref: string | null;
  result_image_path: string | null;
  result_image_b64: string | null;
  size_recommendation: string | null;
  fit_notes: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface AppState {
  // Navigation
  currentPage: 'scan' | 'wardrobe' | 'tryon' | 'advisor' | 'settings';
  setCurrentPage: (page: AppState['currentPage']) => void;

  // Body profile
  activeProfile: BodyProfile | null;
  setActiveProfile: (profile: BodyProfile | null) => void;

  // Wardrobe
  wardrobeItems: WardrobeItem[];
  setWardrobeItems: (items: WardrobeItem[]) => void;

  // Try-on
  tryOnResult: TryOnResult | null;
  setTryOnResult: (result: TryOnResult | null) => void;
  isTryOnLoading: boolean;
  setTryOnLoading: (loading: boolean) => void;

  // Advisor chat
  chatMessages: ChatMessage[];
  addChatMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearChat: () => void;

  // Backend connection
  backendConnected: boolean;
  setBackendConnected: (connected: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Navigation
      currentPage: 'scan',
      setCurrentPage: (page) => set({ currentPage: page }),

      // Body profile
      activeProfile: null,
      setActiveProfile: (profile) => set({ activeProfile: profile }),

      // Wardrobe
      wardrobeItems: [],
      setWardrobeItems: (items) => set({ wardrobeItems: items }),

      // Try-on
      tryOnResult: null,
      setTryOnResult: (result) => set({ tryOnResult: result }),
      isTryOnLoading: false,
      setTryOnLoading: (loading) => set({ isTryOnLoading: loading }),

      // Advisor chat
      chatMessages: [],
      addChatMessage: (message) =>
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: Date.now(),
            },
          ],
        })),
      clearChat: () => set({ chatMessages: [] }),

      // Backend connection
      backendConnected: false,
      setBackendConnected: (connected) => set({ backendConnected: connected }),
    }),
    { name: 'wardrobe-twin-store' }
  )
);
