import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import Slider from '@mui/material/Slider'
import LinearProgress from '@mui/material/LinearProgress'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import IconButton from '@mui/material/IconButton'
import FolderIcon from '@mui/icons-material/Folder'
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import axios from 'axios'
import useSkinStore from '../store/skinStore'

const API_BASE_URL = '/api/v1'

interface AudioOutput {
  id: number
  name: string
  active: boolean
}

interface PerformanceMetrics {
  memory: { percent: number; used_bytes: number; total_bytes: number }
  storage: { percent: number; used_bytes: number; total_bytes: number }
  temperature_c: number | null
  load: { one_minute: number; five_minutes: number; fifteen_minutes: number }
  uptime_seconds: number
  processes: number
}

interface SambaShare {
  name: string
  path: string
  read_only: boolean
  guest_ok: boolean
  server?: string
  smb_url?: string
}

interface SambaFileEntry {
  name: string
  is_dir: boolean
  size: number
  permissions: string
  owner: string
  group: string
  modified: number
}

export default function Settings() {
  const [scanStatus, setScanStatus] = React.useState('idle')
  const [volume, setVolume] = React.useState(50)
  const [volumeError, setVolumeError] = React.useState<string | null>(null)
  const [scanMessage, setScanMessage] = React.useState<string | null>(null)
  const [outputs, setOutputs] = React.useState<AudioOutput[]>([])
  const [outputError, setOutputError] = React.useState<string | null>(null)
  const [performance, setPerformance] = React.useState<PerformanceMetrics | null>(null)
  const {
    hasImage,
    settings: skinSettings,
    imageVersion,
    error: skinError,
    fetchSkin,
    uploadSkin,
    updateSettings: updateSkinSettings,
    removeSkin,
  } = useSkinStore()
  const [uploading, setUploading] = React.useState(false)
  const [sambaActive, setSambaActive] = React.useState(false)
  const [sambaShare, setSambaShare] = React.useState<SambaShare | null>(null)
  const [sambaName, setSambaName] = React.useState('TouchPlayerShare')
  const [sambaPath, setSambaPath] = React.useState('/home/pi/Shared')
  const [sambaReadOnly, setSambaReadOnly] = React.useState(false)
  const [sambaGuestOk, setSambaGuestOk] = React.useState(true)
  const [sambaError, setSambaError] = React.useState<string | null>(null)
  const [sambaSaving, setSambaSaving] = React.useState(false)
  const [sambaFiles, setSambaFiles] = React.useState<SambaFileEntry[]>([])
  const [sambaCurrentPath, setSambaCurrentPath] = React.useState('')
  const [sambaFilesError, setSambaFilesError] = React.useState<string | null>(null)

  const loadSambaFiles = React.useCallback(async (subpath: string = '') => {
    setSambaFilesError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/samba/files`, { params: { path: subpath } })
      setSambaFiles(response.data?.entries || [])
      setSambaCurrentPath(response.data?.path || '')
    } catch (error: any) {
      setSambaFiles([])
      setSambaFilesError(error?.response?.data?.detail || 'No shared folder to browse yet')
    }
  }, [])

  const loadSamba = React.useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/samba`)
      setSambaActive(Boolean(response.data?.active))
      const share: SambaShare | null = response.data?.share ?? null
      setSambaShare(share)
      if (share) {
        setSambaName(share.name)
        setSambaPath(share.path)
        setSambaReadOnly(share.read_only)
        setSambaGuestOk(share.guest_ok)
      }
    } catch (error) {
      console.error('Failed to load Samba share:', error)
    }
  }, [])

  const loadOutputs = React.useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/playback/outputs`)
      setOutputs(response.data?.outputs || [])
    } catch (error) {
      console.error('Failed to load audio outputs:', error)
      setOutputError('Failed to load audio devices')
    }
  }, [])

  React.useEffect(() => {
    const loadVolume = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/playback/status`)
        const currentVolume = Number(response.data?.output_volume ?? response.data?.status?.volume)
        if (Number.isFinite(currentVolume) && currentVolume >= 0) {
          setVolume(currentVolume)
        }
      } catch (error) {
        console.error('Failed to load volume:', error)
        setVolumeError('Failed to load volume')
      }
    }

    loadVolume()
    loadOutputs()
  }, [loadOutputs])

  React.useEffect(() => {
    fetchSkin()
  }, [fetchSkin])

  React.useEffect(() => {
    loadSamba()
  }, [loadSamba])

  React.useEffect(() => {
    if (sambaShare) {
      loadSambaFiles('')
    } else {
      setSambaFiles([])
    }
  }, [sambaShare, loadSambaFiles])

  React.useEffect(() => {
    if (!sambaShare) return
    const interval = setInterval(() => loadSambaFiles(sambaCurrentPath), 5000)
    return () => clearInterval(interval)
  }, [sambaShare, sambaCurrentPath, loadSambaFiles])

  React.useEffect(() => {
    let active = true
    const loadPerformance = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/settings/performance`)
        if (active) setPerformance(response.data)
      } catch (error) {
        console.error('Failed to load system performance:', error)
      }
    }
    loadPerformance()
    const interval = setInterval(loadPerformance, 5000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  const formatBytes = (bytes: number) => {
    const units = ['B', 'GB', 'TB']
    let value = bytes
    let unit = 0
    while (value >= 1024 ** 3 && unit < units.length - 1) {
      value /= 1024 ** 3
      unit += 1
    }
    return `${value.toFixed(1)} ${units[unit]}`
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const handleSelectOutput = async (sinkId: number) => {
    setOutputError(null)
    try {
      await axios.post(`${API_BASE_URL}/playback/output`, null, { params: { sink_id: sinkId } })
      await loadOutputs()
    } catch (error) {
      console.error('Failed to set audio output:', error)
      setOutputError('Failed to change audio device')
    }
  }

  const handleVolumeCommit = async (newVolume: number) => {
    setVolumeError(null)
    try {
      await axios.post(`${API_BASE_URL}/playback/volume`, null, {
        params: { volume: newVolume },
      })
    } catch (error) {
      console.error('Failed to set volume:', error)
      setVolumeError('Failed to change volume')
    }
  }

  const handleScan = async () => {
    setScanStatus('scanning')
    setScanMessage(null)
    try {
      await axios.post(`${API_BASE_URL}/settings/scan`)
      for (let attempt = 0; attempt < 600; attempt += 1) {
        const response = await axios.get(`${API_BASE_URL}/settings/scan/status`)
        const status = response.data
        setScanMessage(`Scanning ${status.processed_files || 0}/${status.total_files || 0} files...`)
        if (status.status === 'completed') {
          setScanMessage(`Scan complete: ${status.total_files} files, new ${status.new_files || 0}, modified ${status.modified_files || 0}, deleted ${status.deleted_files || 0}`)
          setScanStatus('complete')
          return
        }
        if (status.status === 'failed') {
          throw new Error(status.error || 'Media scan failed')
        }
        await new Promise((resolve) => setTimeout(resolve, 1000))
      }
      throw new Error('Media scan timed out')
    } catch (error) {
      console.error('Scan failed:', error)
      setScanStatus('error')
      setScanMessage('Media scan failed')
    }
  }

  const handleSkinUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true)
    await uploadSkin(file)
    setUploading(false)
  }

  const handleApplySamba = async () => {
    setSambaError(null)
    setSambaSaving(true)
    try {
      await axios.post(`${API_BASE_URL}/samba`, {
        name: sambaName.trim(),
        path: sambaPath.trim(),
        read_only: sambaReadOnly,
        guest_ok: sambaGuestOk,
      })
      await loadSamba()
      await loadSambaFiles('')
    } catch (error: any) {
      console.error('Failed to configure Samba share:', error)
      setSambaError(error?.response?.data?.detail || 'Failed to configure shared folder')
    } finally {
      setSambaSaving(false)
    }
  }

  const handleRemoveSamba = async () => {
    setSambaError(null)
    setSambaSaving(true)
    try {
      await axios.delete(`${API_BASE_URL}/samba`)
      setSambaShare(null)
      setSambaFiles([])
      await loadSamba()
    } catch (error) {
      console.error('Failed to remove Samba share:', error)
      setSambaError('Failed to remove shared folder')
    } finally {
      setSambaSaving(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    const units = ['KB', 'MB', 'GB']
    let value = bytes / 1024
    let unit = 0
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024
      unit += 1
    }
    return `${value.toFixed(1)} ${units[unit]}`
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Media Library
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Scan Status: {scanStatus}
                </Typography>
                {scanMessage && (
                  <Typography variant="body2" color={scanStatus === 'error' ? 'error' : 'text.secondary'}>
                    {scanMessage}
                  </Typography>
                )}
              </Box>
              
              <Button variant="contained" onClick={handleScan}>
                Scan Library
              </Button>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Audio
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Volume: {volume}%
                </Typography>
                <Slider
                  min={0}
                  max={100}
                  value={volume}
                  onChange={(_event, newValue) => setVolume(newValue as number)}
                  onChangeCommitted={(_event, newValue) => handleVolumeCommit(newValue as number)}
                  aria-label="Volume"
                  sx={{ mt: 1 }}
                />
                {volumeError && (
                  <Typography variant="body2" color="error">
                    {volumeError}
                  </Typography>
                )}
              </Box>

              <Typography variant="subtitle2" gutterBottom>
                Output Device
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {outputs.map((output) => (
                  <Button
                    key={output.id}
                    variant={output.active ? 'contained' : 'outlined'}
                    onClick={() => handleSelectOutput(output.id)}
                  >
                    {output.name}
                  </Button>
                ))}
                {outputs.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No audio devices found.
                  </Typography>
                )}
                {outputError && (
                  <Typography variant="body2" color="error">
                    {outputError}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Network Share (Samba)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Samba service: {sambaActive ? 'Running' : 'Stopped'}
                {sambaShare ? ` · Sharing "${sambaShare.name}"` : ' · No shared folder configured'}
              </Typography>
              {sambaShare?.smb_url && (
                <Typography variant="body2" sx={{ mb: 2, fontFamily: 'monospace' }}>
                  Connect from another device: {sambaShare.smb_url}
                </Typography>
              )}

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  size="small"
                  label="Share Name"
                  value={sambaName}
                  onChange={(event) => setSambaName(event.target.value)}
                />
                <TextField
                  size="small"
                  label="Folder Path"
                  value={sambaPath}
                  onChange={(event) => setSambaPath(event.target.value)}
                  helperText="Created automatically if it doesn't exist"
                />
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <FormControlLabel
                    control={<Checkbox checked={sambaGuestOk} onChange={(event) => setSambaGuestOk(event.target.checked)} />}
                    label="Guest Access"
                  />
                  <FormControlLabel
                    control={<Checkbox checked={sambaReadOnly} onChange={(event) => setSambaReadOnly(event.target.checked)} />}
                    label="Read Only"
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="contained"
                    onClick={handleApplySamba}
                    disabled={sambaSaving || !sambaName.trim() || !sambaPath.trim()}
                  >
                    {sambaSaving ? 'Saving...' : sambaShare ? 'Update Share' : 'Create Share'}
                  </Button>
                  {sambaShare && (
                    <Button variant="outlined" color="error" onClick={handleRemoveSamba} disabled={sambaSaving}>
                      Remove Share
                    </Button>
                  )}
                </Box>
                {sambaError && (
                  <Typography variant="body2" color="error">
                    {sambaError}
                  </Typography>
                )}
              </Box>

              {sambaShare && (
                <Box sx={{ mt: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="subtitle2">
                      Shared Folder Contents: /{sambaCurrentPath}
                    </Typography>
                    <IconButton
                      size="small"
                      disabled={!sambaCurrentPath}
                      onClick={() => loadSambaFiles(sambaCurrentPath.split('/').slice(0, -1).join('/'))}
                      title="Go up one level"
                    >
                      <ArrowUpwardIcon fontSize="small" />
                    </IconButton>
                    <Button size="small" onClick={() => loadSambaFiles(sambaCurrentPath)}>
                      Refresh
                    </Button>
                  </Box>

                  {sambaFilesError && (
                    <Typography variant="body2" color="text.secondary">
                      {sambaFilesError}
                    </Typography>
                  )}

                  {!sambaFilesError && (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Permissions</TableCell>
                            <TableCell>Owner</TableCell>
                            <TableCell align="right">Size</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {sambaFiles.map((entry) => (
                            <TableRow
                              key={entry.name}
                              hover={entry.is_dir}
                              sx={{ cursor: entry.is_dir ? 'pointer' : 'default' }}
                              onClick={() => {
                                if (entry.is_dir) {
                                  const nextPath = sambaCurrentPath ? `${sambaCurrentPath}/${entry.name}` : entry.name
                                  loadSambaFiles(nextPath)
                                }
                              }}
                            >
                              <TableCell>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  {entry.is_dir ? <FolderIcon fontSize="small" /> : <InsertDriveFileIcon fontSize="small" />}
                                  {entry.name}
                                </Box>
                              </TableCell>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{entry.permissions}</TableCell>
                              <TableCell>{entry.owner}:{entry.group}</TableCell>
                              <TableCell align="right">{entry.is_dir ? '—' : formatFileSize(entry.size)}</TableCell>
                            </TableRow>
                          ))}
                          {sambaFiles.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={4}>
                                <Typography variant="body2" color="text.secondary">
                                  This folder is empty.
                                </Typography>
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Appearance / Skin
              </Typography>

              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <Box
                  sx={{
                    width: 160,
                    height: 100,
                    borderRadius: 1,
                    border: '1px solid rgba(255,255,255,0.2)',
                    backgroundImage: hasImage ? `url(/api/v1/skin/image?v=${imageVersion})` : undefined,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {!hasImage && (
                    <Typography variant="caption" color="text.secondary">No skin set</Typography>
                  )}
                </Box>

                <Box sx={{ flex: 1, minWidth: 260 }}>
                  <Button variant="contained" component="label" disabled={uploading}>
                    {uploading ? 'Uploading...' : 'Upload Background Image'}
                    <input type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={handleSkinUpload} />
                  </Button>
                  {hasImage && (
                    <Button variant="outlined" color="error" sx={{ ml: 1 }} onClick={removeSkin}>
                      Remove Skin
                    </Button>
                  )}
                  {skinError && (
                    <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                      {skinError}
                    </Typography>
                  )}
                </Box>
              </Box>

              {hasImage && (
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Fit</Typography>
                    <Select
                      size="small"
                      fullWidth
                      value={skinSettings.fit}
                      onChange={(event) => updateSkinSettings({ fit: event.target.value as typeof skinSettings.fit })}
                    >
                      <MenuItem value="cover">Cover</MenuItem>
                      <MenuItem value="contain">Contain</MenuItem>
                      <MenuItem value="repeat">Repeat</MenuItem>
                    </Select>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Opacity: {Math.round(skinSettings.opacity * 100)}%</Typography>
                    <Slider
                      min={0}
                      max={1}
                      step={0.05}
                      value={skinSettings.opacity}
                      onChange={(_event, value) => updateSkinSettings({ opacity: value as number })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Blur: {skinSettings.blur}px</Typography>
                    <Slider
                      min={0}
                      max={20}
                      step={1}
                      value={skinSettings.blur}
                      onChange={(_event, value) => updateSkinSettings({ blur: value as number })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Brightness: {Math.round(skinSettings.brightness * 100)}%</Typography>
                    <Slider
                      min={0.2}
                      max={1.5}
                      step={0.05}
                      value={skinSettings.brightness}
                      onChange={(_event, value) => updateSkinSettings({ brightness: value as number })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Overlay Darkness: {Math.round(skinSettings.overlay_opacity * 100)}%</Typography>
                    <Slider
                      min={0}
                      max={1}
                      step={0.05}
                      value={skinSettings.overlay_opacity}
                      onChange={(_event, value) => updateSkinSettings({ overlay_opacity: value as number })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="body2">Overlay Color</Typography>
                    <input
                      type="color"
                      value={skinSettings.overlay_color}
                      onChange={(event) => updateSkinSettings({ overlay_color: event.target.value })}
                      style={{ width: '100%', height: 36, border: 'none', background: 'none' }}
                    />
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Performance
              </Typography>
              {!performance ? (
                <Typography variant="body2" color="text.secondary">Loading performance metrics...</Typography>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Typography variant="body2">Memory: {performance.memory.percent}%</Typography>
                    <LinearProgress variant="determinate" value={performance.memory.percent} sx={{ mt: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      {formatBytes(performance.memory.used_bytes)} / {formatBytes(performance.memory.total_bytes)}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Typography variant="body2">Storage: {performance.storage.percent}%</Typography>
                    <LinearProgress variant="determinate" value={performance.storage.percent} sx={{ mt: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      {formatBytes(performance.storage.used_bytes)} / {formatBytes(performance.storage.total_bytes)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={2}>
                    <Typography variant="body2">Temperature</Typography>
                    <Typography variant="h6">{performance.temperature_c === null ? 'N/A' : `${performance.temperature_c}°C`}</Typography>
                  </Grid>
                  <Grid item xs={6} md={2}>
                    <Typography variant="body2">Load (1m)</Typography>
                    <Typography variant="h6">{performance.load.one_minute.toFixed(2)}</Typography>
                  </Grid>
                  <Grid item xs={6} md={2}>
                    <Typography variant="body2">Uptime</Typography>
                    <Typography variant="h6">{formatUptime(performance.uptime_seconds)}</Typography>
                    <Typography variant="caption" color="text.secondary">{performance.processes} processes</Typography>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

      </Grid>
    </Box>
  )
}
