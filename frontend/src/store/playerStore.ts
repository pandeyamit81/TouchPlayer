import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface PlayerState {
  // Playback state
  isPlaying: boolean
  isPaused: boolean
  isStopped: boolean
  
  // Current track
  currentTrack: Track | null
  queue: Track[]
  
  // Volume
  volume: number
  
  // Playback modes
  repeat: boolean
  random: boolean
  single: boolean
  crossfade: number

  // Progress (seconds)
  elapsed: number
  duration: number
  songId: number | null
  
  // Actions
  play: () => void
  pause: () => void
  stop: () => void
  next: () => void
  previous: () => void
  seek: (time: number) => void
  setVolume: (volume: number) => void
  toggleRepeat: () => void
  toggleRandom: () => void
  toggleSingle: () => void
  setCrossfade: (seconds: number) => void
  addToQueue: (track: Track) => void
  removeFromQueue: (index: number) => void
  clearQueue: () => void
  playTrack: (track: Track) => void
  playQueuePosition: (position: number) => void
  syncStatus: () => void
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
  play_count?: number
  favorite?: boolean
}

const usePlayerStore = create<PlayerState>()(
  devtools(
    persist(
      (set, get) => ({
        // State
        isPlaying: false,
        isPaused: false,
        isStopped: true,
        currentTrack: null,
        queue: [],
        volume: 50,
        repeat: false,
        random: false,
        single: false,
        crossfade: 0,
        elapsed: 0,
        duration: 0,
        songId: null,
        
        // Actions
        play: async () => {
          try {
            await axios.post(`${API_BASE_URL}/playback/play`)
            set({ isPlaying: true, isPaused: false, isStopped: false })
          } catch (error) {
            console.error('Failed to play:', error)
          }
        },
        
        pause: async () => {
          try {
            await axios.post(`${API_BASE_URL}/playback/pause`, null, { params: { pause: true } })
            set({ isPaused: true, isPlaying: false })
          } catch (error) {
            console.error('Failed to pause:', error)
          }
        },
        
        stop: async () => {
          try {
            await axios.post(`${API_BASE_URL}/playback/stop`)
            set({ isPlaying: false, isPaused: false, isStopped: true })
          } catch (error) {
            console.error('Failed to stop:', error)
          }
        },
        
        next: async () => {
          try {
            await axios.post(`${API_BASE_URL}/playback/next`)
            get().syncStatus()
          } catch (error) {
            console.error('Failed to skip to next:', error)
          }
        },
        
        previous: async () => {
          try {
            await axios.post(`${API_BASE_URL}/playback/previous`)
            get().syncStatus()
          } catch (error) {
            console.error('Failed to go to previous:', error)
          }
        },
        
        seek: async (time: number) => {
          const { songId } = get()
          if (songId === null) return
          set({ elapsed: time })
          try {
            await axios.post(`${API_BASE_URL}/playback/seek`, null, {
              params: { song_id: songId, time_pos: Math.round(time) },
            })
          } catch (error) {
            console.error('Failed to seek:', error)
          }
        },
        
        setVolume: async (volume: number) => {
          set({ volume })
          try {
            await axios.post(`${API_BASE_URL}/playback/volume`, null, { params: { volume } })
          } catch (error) {
            console.error('Failed to set volume:', error)
          }
        },
        
        toggleRepeat: () => set((state) => ({ repeat: !state.repeat })),
        
        toggleRandom: () => set((state) => ({ random: !state.random })),
        
        toggleSingle: () => set((state) => ({ single: !state.single })),
        
        setCrossfade: (seconds: number) => set({ crossfade: seconds }),
        
        addToQueue: (track: Track) => set((state) => ({
          queue: [...state.queue, track],
        })),
        
        removeFromQueue: (index: number) => set((state) => ({
          queue: state.queue.filter((_, i) => i !== index),
        })),
        
        clearQueue: () => set({ queue: [] }),
        
        playTrack: async (track: Track) => {
          set({
            currentTrack: track,
            isPlaying: true,
            isPaused: false,
            isStopped: false,
          })
          try {
            await axios.post(`${API_BASE_URL}/queue/play/${track.id}`)
          } catch (error) {
            console.error('Failed to play track:', error)
          }
        },
        
        playQueuePosition: async (position: number) => {
          try {
            await axios.post(`${API_BASE_URL}/queue/play/position/${position}`)
            get().syncStatus()
          } catch (error) {
            console.error('Failed to play queue position:', error)
          }
        },
        
        syncStatus: async () => {
          try {
            const response = await axios.get(`${API_BASE_URL}/playback/status`)
            const status = response.data?.status ?? {}
            const outputVolume = Number(response.data?.output_volume)
            const song = response.data?.current_song ?? {}
            const state = status.state
            const volume = Number(status.volume)
            const elapsed = Number(status.elapsed)
            const duration = Number(status.duration)
            const songId = Number(status.songid)
            const hasSong = song && Object.keys(song).length > 0

            set((prev) => ({
              isPlaying: state === 'play',
              isPaused: state === 'pause',
              isStopped: state === 'stop' || !state,
              volume: Number.isFinite(outputVolume) && outputVolume >= 0
                ? outputVolume
                : (Number.isFinite(volume) && volume >= 0 ? volume : prev.volume),
              elapsed: Number.isFinite(elapsed) ? elapsed : 0,
              duration: Number.isFinite(duration) && duration > 0
                ? duration
                : Number(song.time ?? song.duration ?? prev.duration ?? 0),
              songId: Number.isFinite(songId) ? songId : null,
              currentTrack: hasSong
                ? {
                    id: Number(song.id ?? prev.currentTrack?.id ?? 0),
                    file_path: song.file ?? prev.currentTrack?.file_path ?? '',
                    title: song.title ?? (song.file ? String(song.file).split('/').pop() : 'Unknown') ?? 'Unknown',
                    artist: song.artist ?? 'Unknown Artist',
                    album: song.album ?? 'Unknown Album',
                    duration: Number(song.time ?? song.duration ?? prev.currentTrack?.duration ?? 0),
                  }
                : state === 'stop' ? null : prev.currentTrack,
            }))
          } catch (error) {
            console.error('Failed to sync status:', error)
          }
        },
      }),
      {
        name: 'touchplayer-player',
      }
    )
  )
)

export default usePlayerStore
