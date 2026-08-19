import React from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import BluetoothIcon from '@mui/icons-material/Bluetooth'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface BluetoothDevice {
  address: string
  name: string
  connected: boolean
  paired: boolean
}

export default function Bluetooth() {
  const theme = useTheme()

  const [devices, setDevices] = React.useState<BluetoothDevice[]>([])
  const [scanning, setScanning] = React.useState(false)
  const [updatingAddress, setUpdatingAddress] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  const loadDevices = React.useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/bluetooth/devices`)
      setDevices(response.data.devices || [])
    } catch (err) {
      console.error('Failed to load Bluetooth devices:', err)
      setError('Failed to load Bluetooth devices')
    }
  }, [])

  React.useEffect(() => {
    loadDevices()
  }, [loadDevices])

  const scanDevices = async () => {
    setScanning(true)
    setError(null)
    try {
      await axios.post(`${API_BASE_URL}/bluetooth/scan`)
      await loadDevices()
    } catch (err) {
      console.error('Failed to scan devices:', err)
      setError('Bluetooth scan failed')
    }
    setScanning(false)
  }

  const updateDeviceConnection = async (device: BluetoothDevice) => {
    setUpdatingAddress(device.address)
    setError(null)
    try {
      const action = device.connected ? 'disconnect' : 'connect'
      await axios.post(`${API_BASE_URL}/bluetooth/${action}/${encodeURIComponent(device.address)}`)
      await loadDevices()
    } catch (err) {
      console.error('Failed to update Bluetooth device:', err)
      setError(`Failed to ${device.connected ? 'disconnect' : 'connect'} ${device.name || device.address}`)
    }
    setUpdatingAddress(null)
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Bluetooth
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Button variant="contained" onClick={scanDevices} disabled={scanning}>
          {scanning ? 'Scanning...' : 'Scan Devices'}
        </Button>
      </Box>

      {error && (
        <Typography variant="body2" color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      
      <Grid container spacing={2}>
        {devices.length === 0 && !scanning && (
          <Grid item xs={12}>
            <Typography variant="body1" color="text.secondary">
              No paired Bluetooth devices found.
            </Typography>
          </Grid>
        )}
        {devices.map((device) => (
          <Grid item xs={12} key={device.address}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <BluetoothIcon
                    sx={{
                      color: device.connected ? theme.palette.success.main : theme.palette.primary.main,
                      fontSize: 48,
                    }}
                  />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {device.name || 'Unknown device'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {device.address}
                    </Typography>
                    <Typography variant="body2" color={device.connected ? 'success.main' : 'text.secondary'}>
                      {device.connected ? 'Connected' : device.paired ? 'Paired' : 'Available'}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    color={device.connected ? 'error' : 'primary'}
                    disabled={updatingAddress === device.address}
                    onClick={() => updateDeviceConnection(device)}
                  >
                    {updatingAddress === device.address
                      ? device.connected ? 'Disconnecting...' : 'Connecting...'
                      : device.connected ? 'Disconnect' : 'Connect'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
