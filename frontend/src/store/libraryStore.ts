import { create } from 'zustand'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface LibraryState {
  // Data
  tracks: Track[]
  albums: Album[]
  artists: Artist[]
  
  // Loading states
  isLoadingTracks: boolean
  isLoadingAlbums: boolean
  isLoadingArtists: boolean
  
  // Actions
  fetchTracks: (params?: any) => Promise<void>
  fetchAlbums: (params?: any) => Promise<void>
  fetchArtists: (params?: any) => Promise<void>
  searchMusic: (query: string) => Promise<void>
  getMusicStats: () => Promise<void>
}

interface Track {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
  track_number?: number
  disc_number?: number
  year?: number
  genre?: string
  play_count?: number
  favorite?: boolean
  added_at?: string
}

interface Album {
  id: number
  name: string
  artist: string
  year?: number
  genre?: string
  track_count?: number
  duration?: number
  has_artwork?: boolean
  added_at?: string
}

interface Artist {
  id: number
  name: string
  sort_name?: string
  genre?: string
  track_count?: number
  album_count?: number
  play_count?: number
  added_at?: string
}

const useLibraryStore = create<LibraryState>((set, get) => ({
  // State
  tracks: [],
  albums: [],
  artists: [],
  isLoadingTracks: false,
  isLoadingAlbums: false,
  isLoadingArtists: false,
  
  // Actions
  fetchTracks: async (params = {}) => {
    set({ isLoadingTracks: true })
    try {
      const response = await axios.get(`${API_BASE_URL}/music`, { params })
      set({ tracks: response.data.tracks, isLoadingTracks: false })
    } catch (error) {
      console.error('Failed to fetch tracks:', error)
      set({ isLoadingTracks: false })
    }
  },
  
  fetchAlbums: async (params = {}) => {
    set({ isLoadingAlbums: true })
    try {
      const response = await axios.get(`${API_BASE_URL}/albums`, { params })
      set({ albums: response.data.albums, isLoadingAlbums: false })
    } catch (error) {
      console.error('Failed to fetch albums:', error)
      set({ isLoadingAlbums: false })
    }
  },
  
  fetchArtists: async (params = {}) => {
    set({ isLoadingArtists: true })
    try {
      const response = await axios.get(`${API_BASE_URL}/artists`, { params })
      set({ artists: response.data.artists, isLoadingArtists: false })
    } catch (error) {
      console.error('Failed to fetch artists:', error)
      set({ isLoadingArtists: false })
    }
  },
  
  searchMusic: async (query: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/music/search`, {
        params: { query, limit: 50 },
      })
      set({ tracks: response.data.tracks })
    } catch (error) {
      console.error('Failed to search music:', error)
    }
  },
  
  getMusicStats: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/music/stats`)
      console.log('Music stats:', response.data)
    } catch (error) {
      console.error('Failed to get music stats:', error)
    }
  },
}))

export default useLibraryStore
