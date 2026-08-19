import { create } from 'zustand'

const SECRET_MENU_DURATION_MS = 10 * 60 * 1000

interface SecretMenuState {
  enabled: boolean
  expiresAt: number | null
  enable: () => void
  disable: () => void
}

const useSecretMenuStore = create<SecretMenuState>((set) => ({
  enabled: false,
  expiresAt: null,
  enable: () => set({ enabled: true, expiresAt: Date.now() + SECRET_MENU_DURATION_MS }),
  disable: () => set({ enabled: false, expiresAt: null }),
}))

export default useSecretMenuStore
