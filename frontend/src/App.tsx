import { Routes, Route, Navigate } from 'react-router-dom'

// Pages
import Home from './pages/Home'
import NowPlaying from './pages/NowPlaying'
import Library from './pages/Library'
import Albums from './pages/Albums'
import Artists from './pages/Artists'
import Videos from './pages/Videos'
import Playlists from './pages/Playlists'
import Bluetooth from './pages/Bluetooth'
import WiFi from './pages/WiFi'
import Settings from './pages/Settings'
import SMS from './pages/SMS'
import useSecretMenuStore from './store/secretMenuStore'

// Components
import Layout from './components/Layout'
import PlayerControls from './components/PlayerControls'

function App() {
  const smsEnabled = useSecretMenuStore((state) => state.enabled)

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/now-playing" element={<NowPlaying />} />
        <Route path="/library" element={<Library />} />
        <Route path="/albums" element={<Albums />} />
        <Route path="/artists" element={<Artists />} />
        <Route path="/videos" element={<Videos />} />
        <Route path="/playlists" element={<Playlists />} />
        <Route path="/bluetooth" element={<Bluetooth />} />
        <Route path="/wifi" element={<WiFi />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/sms" element={smsEnabled ? <SMS /> : <Navigate to="/settings" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      
      {/* Player controls always visible on now playing page */}
      <PlayerControls />
    </Layout>
  )
}

export default App
