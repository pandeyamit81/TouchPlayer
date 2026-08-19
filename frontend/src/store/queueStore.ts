import { create } from 'zustand'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface QueueState {
  // Data
  queue: QueueItem[]
  status: any
  currentSong: any
  
  // Actions
  fetchQueue: () => Promise<void>
  addToQueue: (trackId: number) => Promise<void>
  addToQueueNext: (trackId: number) => Promise<void>
  removeFromQueue: (position?: number, trackId?: number) => Promise<void>
  clearQueue: () => Promise<void>
  moveInQueue: (fromPosition: number, toPosition: number) => Promise<void>
  playTrack: (trackId: number) => Promise<void>
  playQueuePosition: (position: number) => Promise<void>
}

interface QueueItem {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
  track_number?: number
  play_count?: number
  favorite?: boolean
}

const useQueueStore = create<QueueState>((set, get) => ({
  // State
  queue: [],
  status: null,
  currentSong: null,
  
  // Actions
  fetchQueue: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/queue`)
      set({
        queue: response.data.queue || [],
        status: response.data.status,
        currentSong: response.data.current_song,
      })
    } catch (error) {
      console.error('Failed to fetch queue:', error)
    }
  },
  
  addToQueue: async (trackId: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/add`, null, { params: { track_id: trackId } })
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to add to queue:', error)
      throw error
    }
  },

  addToQueueNext: async (trackId: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/add-next`, null, { params: { track_id: trackId } })
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to add track next:', error)
      throw error
    }
  },
  
  removeFromQueue: async (position?: number, trackId?: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/remove`, {
        position,
        track_id: trackId,
      })
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to remove from queue:', error)
      throw error
    }
  },
  
  clearQueue: async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/clear`)
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to clear queue:', error)
      throw error
    }
  },
  
  moveInQueue: async (fromPosition: number, toPosition: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/move`, {
        from_position: fromPosition,
        to_position: toPosition,
      })
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to move in queue:', error)
      throw error
    }
  },
  
  playTrack: async (trackId: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/play/${trackId}`)
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to play track:', error)
      throw error
    }
  },
  
  playQueuePosition: async (position: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/queue/play/position/${position}`)
      await get().fetchQueue()
      return response.data
    } catch (error) {
      console.error('Failed to play queue position:', error)
      throw error
    }
  },
}))

export default useQueueStore
