import { create } from 'zustand'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface PlaylistState {
  // Data
  playlists: Playlist[]
  currentPlaylist: Playlist | null
  
  // Loading states
  isLoading: boolean
  
  // Actions
  fetchPlaylists: () => Promise<void>
  fetchPlaylist: (id: number) => Promise<void>
  createPlaylist: (name: string, description?: string) => Promise<void>
  updatePlaylist: (id: number, name: string, description?: string) => Promise<void>
  deletePlaylist: (id: number) => Promise<void>
  addTrackToPlaylist: (playlistId: number, trackId: number) => Promise<void>
  removeTrackFromPlaylist: (playlistId: number, trackId: number) => Promise<void>
  playPlaylist: (id: number) => Promise<void>
  getPlaylistTracks: (id: number) => Promise<void>
}

interface Playlist {
  id: number
  name: string
  description?: string
  track_count?: number
  duration?: number
  created_at?: string
  updated_at?: string
  tracks?: PlaylistTrack[]
}

interface PlaylistTrack {
  id: number
  title: string
  artist: string
  album: string
}

const usePlaylistStore = create<PlaylistState>((set, get) => ({
  // State
  playlists: [],
  currentPlaylist: null,
  isLoading: false,
  
  // Actions
  fetchPlaylists: async () => {
    set({ isLoading: true })
    try {
      const response = await axios.get(`${API_BASE_URL}/playlists`)
      set({ playlists: response.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch playlists:', error)
      set({ isLoading: false })
    }
  },
  
  fetchPlaylist: async (id: number) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/playlists/${id}`)
      set({ currentPlaylist: response.data })
    } catch (error) {
      console.error('Failed to fetch playlist:', error)
    }
  },
  
  createPlaylist: async (name: string, description?: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/playlists`, null, {
        params: { name, description },
      })
      await get().fetchPlaylists()
      return response.data
    } catch (error) {
      console.error('Failed to create playlist:', error)
      throw error
    }
  },
  
  updatePlaylist: async (id: number, name: string, description?: string) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/playlists/${id}`, null, {
        params: { name, description },
      })
      await get().fetchPlaylists()
      return response.data
    } catch (error) {
      console.error('Failed to update playlist:', error)
      throw error
    }
  },
  
  deletePlaylist: async (id: number) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/playlists/${id}`)
      await get().fetchPlaylists()
      return response.data
    } catch (error) {
      console.error('Failed to delete playlist:', error)
      throw error
    }
  },
  
  addTrackToPlaylist: async (playlistId: number, trackId: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/playlists/${playlistId}/tracks`, null, {
        params: { track_id: trackId },
      })
      await get().fetchPlaylists()
      return response.data
    } catch (error) {
      console.error('Failed to add track to playlist:', error)
      throw error
    }
  },
  
  removeTrackFromPlaylist: async (playlistId: number, trackId: number) => {
    try {
      const response = await axios.delete(
        `${API_BASE_URL}/playlists/${playlistId}/tracks/${trackId}`
      )
      await get().fetchPlaylists()
      return response.data
    } catch (error) {
      console.error('Failed to remove track from playlist:', error)
      throw error
    }
  },
  
  playPlaylist: async (id: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/playlists/${id}/play`)
      return response.data
    } catch (error) {
      console.error('Failed to play playlist:', error)
      throw error
    }
  },
  
  getPlaylistTracks: async (id: number) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/playlists/${id}/tracks`)
      return response.data
    } catch (error) {
      console.error('Failed to get playlist tracks:', error)
      throw error
    }
  },
}))

export default usePlaylistStore
