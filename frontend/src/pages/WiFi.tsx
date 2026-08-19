import React, { useEffect } from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import WifiIcon from '@mui/icons-material/Wifi'
import WifiTetheringIcon from '@mui/icons-material/WifiTethering'
import LockIcon from '@mui/icons-material/Lock'
import LockOpenIcon from '@mui/icons-material/LockOpen'
import useWiFiStore from '../store/wifiStore'

const DEFAULT_HOTSPOT_PASSWORD = 'touchplayer123'

export default function WiFi() {
  const theme = useTheme()
  const { 
    networks, 
    connections, 
    hotspot,
    isHotspotLoading,
    isScanning, 
    isLoadingConnections, 
    scanNetworks, 
    connectNetwork, 
    disconnectNetwork,
    removeConnection,
    loadConnections,
    loadHotspotStatus,
    startHotspot,
    stopHotspot,
    removeHotspot,
  } = useWiFiStore()
  const [hotspotSsid, setHotspotSsid] = React.useState('TouchPlayer')
  const [hotspotPassword, setHotspotPassword] = React.useState(DEFAULT_HOTSPOT_PASSWORD)

  useEffect(() => {
    loadConnections()
    loadHotspotStatus()
  }, [loadConnections, loadHotspotStatus])

  const handleConnect = (ssid: string) => {
    // Check if already connected
    const isConnected = connections.some(c => c.ssid === ssid)
    if (isConnected) {
      // Disconnect instead
      disconnectNetwork(ssid)
    } else {
      // Connect with password prompt
      const password = prompt(`Enter password for ${ssid}:`)
      connectNetwork(ssid, password || undefined)
    }
  }

  const isConnectedToNetwork = (ssid: string) => {
    return connections.some(c => c.ssid === ssid)
  }

  const handleStartHotspot = () => {
    if (!hotspotSsid.trim()) return
    startHotspot(hotspotSsid.trim(), hotspotPassword || DEFAULT_HOTSPOT_PASSWORD)
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        WiFi
      </Typography>

      {/* Access Point / Hotspot */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <WifiTetheringIcon sx={{ color: hotspot.active ? theme.palette.success.main : theme.palette.text.secondary, fontSize: 40 }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6">Access Point (Hotspot)</Typography>
              <Typography variant="body2" color="text.secondary">
                {hotspot.active ? `Broadcasting "${hotspot.ssid}"` : 'Turn this device into a WiFi access point'}
              </Typography>
            </Box>
          </Box>

          {!hotspot.active ? (
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <TextField
                size="small"
                label="Hotspot Name (SSID)"
                value={hotspotSsid}
                onChange={(event) => setHotspotSsid(event.target.value)}
              />
              <TextField
                size="small"
                label={`Password (default: ${DEFAULT_HOTSPOT_PASSWORD})`}
                type="password"
                value={hotspotPassword}
                onChange={(event) => setHotspotPassword(event.target.value)}
              />
              <Button
                variant="contained"
                onClick={handleStartHotspot}
                disabled={isHotspotLoading || !hotspotSsid.trim() || (hotspotPassword.length > 0 && hotspotPassword.length < 8)}
              >
                {isHotspotLoading ? 'Starting...' : 'Start Hotspot'}
              </Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button variant="outlined" onClick={stopHotspot} disabled={isHotspotLoading}>
                Stop Hotspot
              </Button>
              <Button variant="outlined" color="error" onClick={removeHotspot} disabled={isHotspotLoading}>
                Remove Hotspot
              </Button>
            </Box>
          )}
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Starting the hotspot disconnects this device from any WiFi network it is currently joined to.
          </Typography>
        </CardContent>
      </Card>
      
      <Box sx={{ mb: 2 }}>
        <Button variant="contained" onClick={scanNetworks} disabled={isScanning}>
          {isScanning ? 'Scanning...' : 'Scan Networks'}
        </Button>
        <Button 
          variant="outlined" 
          onClick={loadConnections} 
          disabled={isLoadingConnections}
          sx={{ ml: 2 }}
        >
          {isLoadingConnections ? 'Loading...' : 'Refresh Connections'}
        </Button>
      </Box>
      
      {/* Available Networks */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Available Networks
      </Typography>
      
      <Grid container spacing={2}>
        {networks.map((network, index) => {
          const connected = isConnectedToNetwork(network.ssid)
          return (
            <Grid item xs={12} key={index}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    {network.encrypted ? (
                      <LockIcon sx={{ color: theme.palette.warning.main, fontSize: 48 }} />
                    ) : (
                      <LockOpenIcon sx={{ color: theme.palette.warning.main, fontSize: 48 }} />
                    )}
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {network.ssid}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Signal: {network.signal}%
                      </Typography>
                    </Box>
                    <Button 
                      variant="contained" 
                      color={connected ? "error" : "primary"}
                      onClick={() => handleConnect(network.ssid)}
                    >
                      {connected ? 'Disconnect' : 'Connect'}
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          )
        })}
        {networks.length === 0 && !isScanning && (
          <Grid item xs={12}>
            <Typography variant="body1" color="text.secondary">
              No WiFi networks found. Click "Scan Networks" to search.
            </Typography>
          </Grid>
        )}
      </Grid>
      
      {/* Saved Connections */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        Saved Connections
      </Typography>
      
      <Grid container spacing={2}>
        {connections.map((connection, index) => (
          <Grid item xs={12} key={index}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <WifiIcon sx={{ color: theme.palette.primary.main, fontSize: 48 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {connection.ssid || connection.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {connection.autoconnect ? 'Auto-connect: On' : 'Auto-connect: Off'}
                    </Typography>
                  </Box>
                  <Button 
                    variant="outlined" 
                    color="error"
                    onClick={() => removeConnection(connection.name, connection.uuid)}
                  >
                    Remove
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {connections.length === 0 && (
          <Grid item xs={12}>
            <Typography variant="body1" color="text.secondary">
              No saved WiFi connections.
            </Typography>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}
