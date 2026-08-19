import { create } from 'zustand'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

export interface SkinSettings {
  fit: 'cover' | 'contain' | 'repeat'
  opacity: number
  blur: number
  brightness: number
  overlay_color: string
  overlay_opacity: number
}

interface SkinState {
  hasImage: boolean
  settings: SkinSettings
  imageVersion: number
  isLoading: boolean
  error: string | null

  fetchSkin: () => Promise<void>
  uploadSkin: (file: File) => Promise<boolean>
  updateSettings: (updates: Partial<SkinSettings>) => Promise<void>
  removeSkin: () => Promise<void>
}

const DEFAULT_SETTINGS: SkinSettings = {
  fit: 'cover',
  opacity: 1,
  blur: 0,
  brightness: 1,
  overlay_color: '#000000',
  overlay_opacity: 0,
}

const useSkinStore = create<SkinState>((set, get) => ({
  hasImage: false,
  settings: DEFAULT_SETTINGS,
  imageVersion: 0,
  isLoading: false,
  error: null,

  fetchSkin: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get(`${API_BASE_URL}/skin`)
      set({
        hasImage: response.data.has_image,
        settings: { ...DEFAULT_SETTINGS, ...response.data.settings },
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to load skin:', error)
      set({ isLoading: false, error: 'Failed to load skin' })
    }
  },

  uploadSkin: async (file: File) => {
    set({ error: null })
    try {
      const formData = new FormData()
      formData.append('file', file)
      await axios.post(`${API_BASE_URL}/skin/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await get().fetchSkin()
      set((state) => ({ imageVersion: state.imageVersion + 1 }))
      return true
    } catch (error) {
      console.error('Failed to upload skin:', error)
      set({ error: 'Failed to upload image' })
      return false
    }
  },

  updateSettings: async (updates: Partial<SkinSettings>) => {
    set((state) => ({ settings: { ...state.settings, ...updates } }))
    try {
      await axios.put(`${API_BASE_URL}/skin/settings`, updates)
    } catch (error) {
      console.error('Failed to update skin settings:', error)
      set({ error: 'Failed to update skin settings' })
    }
  },

  removeSkin: async () => {
    try {
      await axios.delete(`${API_BASE_URL}/skin`)
      set({ hasImage: false, settings: DEFAULT_SETTINGS })
    } catch (error) {
      console.error('Failed to remove skin:', error)
      set({ error: 'Failed to remove skin' })
    }
  },
}))

export default useSkinStore
