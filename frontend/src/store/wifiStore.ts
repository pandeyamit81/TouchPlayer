import { create } from 'zustand'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface WiFiState {
  // Data
  networks: WiFiNetwork[]
  connections: WiFiConnection[]

  // Hotspot
  hotspot: HotspotStatus
  isHotspotLoading: boolean
  
  // Loading states
  isScanning: boolean
  isLoadingConnections: boolean
  
  // Actions
  scanNetworks: () => Promise<void>
  connectNetwork: (ssid: string, password?: string) => Promise<boolean>
  disconnectNetwork: (ssid?: string) => Promise<boolean>
  removeConnection: (name: string, uuid?: string) => Promise<boolean>
  loadConnections: () => Promise<void>
  loadHotspotStatus: () => Promise<void>
  startHotspot: (ssid: string, password?: string) => Promise<boolean>
  stopHotspot: () => Promise<boolean>
  removeHotspot: () => Promise<boolean>
}

interface HotspotStatus {
  configured: boolean
  active: boolean
  ssid: string | null
}

interface WiFiNetwork {
  ssid: string
  bssid?: string
  mode?: string
  channel?: number
  frequency?: string
  rate?: string
  signal: number
  encrypted: boolean
}

interface WiFiConnection {
  name: string
  uuid?: string
  type?: string
  interface?: string
  ssid?: string
  autoconnect: boolean
  priority: number
}

const useWiFiStore = create<WiFiState>((set, get) => ({
  // State
  networks: [],
  connections: [],
  hotspot: { configured: false, active: false, ssid: null },
  isHotspotLoading: false,
  isScanning: false,
  isLoadingConnections: false,
  
  // Actions
  scanNetworks: async () => {
    set({ isScanning: true })
    try {
      await axios.post(`${API_BASE_URL}/wifi/scan`)
      const response = await axios.get(`${API_BASE_URL}/wifi/networks`)
      set({ 
        networks: response.data.networks || [], 
        isScanning: false 
      })
    } catch (error) {
      console.error('Failed to scan networks:', error)
      set({ isScanning: false })
    }
  },
  
  connectNetwork: async (ssid: string, password?: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/wifi/connect`, null, {
        params: { ssid, password }
      })
      // Reload connections after connecting
      await get().loadConnections()
      return response.data.success || false
    } catch (error) {
      console.error('Failed to connect to network:', error)
      return false
    }
  },
  
  disconnectNetwork: async (ssid?: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/wifi/disconnect`, null, {
        params: { ssid }
      })
      // Reload connections after disconnecting
      await get().loadConnections()
      return response.data.success || false
    } catch (error) {
      console.error('Failed to disconnect from network:', error)
      return false
    }
  },

  removeConnection: async (name: string, uuid?: string) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/wifi/connections`, {
        params: { name, uuid },
      })
      await get().loadConnections()
      return response.data.success || false
    } catch (error) {
      console.error('Failed to remove saved WiFi connection:', error)
      return false
    }
  },
  
  loadConnections: async () => {
    set({ isLoadingConnections: true })
    try {
      const response = await axios.get(`${API_BASE_URL}/wifi/connections`)
      set({ 
        connections: response.data.connections || [], 
        isLoadingConnections: false 
      })
    } catch (error) {
      console.error('Failed to load connections:', error)
      set({ isLoadingConnections: false })
    }
  },

  loadHotspotStatus: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/wifi/hotspot/status`)
      set({ hotspot: response.data })
    } catch (error) {
      console.error('Failed to load hotspot status:', error)
    }
  },

  startHotspot: async (ssid: string, password?: string) => {
    set({ isHotspotLoading: true })
    try {
      await axios.post(`${API_BASE_URL}/wifi/hotspot/start`, null, {
        params: { ssid, password },
      })
      await get().loadHotspotStatus()
      set({ isHotspotLoading: false })
      return true
    } catch (error) {
      console.error('Failed to start hotspot:', error)
      set({ isHotspotLoading: false })
      return false
    }
  },

  stopHotspot: async () => {
    set({ isHotspotLoading: true })
    try {
      await axios.post(`${API_BASE_URL}/wifi/hotspot/stop`)
      await get().loadHotspotStatus()
      set({ isHotspotLoading: false })
      return true
    } catch (error) {
      console.error('Failed to stop hotspot:', error)
      set({ isHotspotLoading: false })
      return false
    }
  },

  removeHotspot: async () => {
    set({ isHotspotLoading: true })
    try {
      await axios.delete(`${API_BASE_URL}/wifi/hotspot`)
      set({ hotspot: { configured: false, active: false, ssid: null }, isHotspotLoading: false })
      return true
    } catch (error) {
      console.error('Failed to remove hotspot:', error)
      set({ isHotspotLoading: false })
      return false
    }
  }
}))

export default useWiFiStore
