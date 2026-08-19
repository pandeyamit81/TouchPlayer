import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import IconButton from '@mui/material/IconButton'
import Slider from '@mui/material/Slider'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import VolumeUpIcon from '@mui/icons-material/VolumeUp'
import VolumeOffIcon from '@mui/icons-material/VolumeOff'
import FullscreenIcon from '@mui/icons-material/Fullscreen'
import CloseIcon from '@mui/icons-material/Close'
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface VideoItem {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
}

const formatTime = (seconds: number) => {
  if (!Number.isFinite(seconds)) return '0:00'
  return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`
}

export default function Videos() {
  const videoRef = React.useRef<HTMLVideoElement>(null)
  const playerRef = React.useRef<HTMLDivElement>(null)
  const [videos, setVideos] = React.useState<VideoItem[]>([])
  const [selectedVideo, setSelectedVideo] = React.useState<VideoItem | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [currentTime, setCurrentTime] = React.useState(0)
  const [duration, setDuration] = React.useState(0)
  const [volume, setVolume] = React.useState(1)
  const [muted, setMuted] = React.useState(false)
  const [speed, setSpeed] = React.useState(1)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    axios.get(`${API_BASE_URL}/videos`, { params: { limit: 5000 } })
      .then((response) => setVideos(response.data.videos || []))
      .catch(() => setError('Unable to load scanned videos'))
  }, [])

  React.useEffect(() => {
    const video = videoRef.current
    if (!video) return
    video.volume = volume
    video.muted = muted
    video.playbackRate = speed
  }, [volume, muted, speed, selectedVideo])

  const openVideo = (video: VideoItem) => {
    setSelectedVideo(video)
    setCurrentTime(0)
    setIsPlaying(false)
  }

  const closeVideo = () => {
    videoRef.current?.pause()
    setSelectedVideo(null)
    setIsPlaying(false)
  }

  const togglePlay = async () => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) await video.play()
    else video.pause()
  }

  const toggleFullscreen = async () => {
    if (!playerRef.current) return
    if (document.fullscreenElement) await document.exitFullscreen()
    else await playerRef.current.requestFullscreen()
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Videos
      </Typography>
      {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
      {!error && videos.length === 0 && (
        <Typography variant="body1" color="text.secondary">No scanned video files found.</Typography>
      )}
      <Grid container spacing={2}>
        {videos.map((video) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={video.id}>
            <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => openVideo(video)}>
              <CardContent>
                <VideoLibraryIcon color="primary" sx={{ fontSize: 48, mb: 1 }} />
                <Typography variant="body1" fontWeight="bold" noWrap>{video.title}</Typography>
                <Typography variant="body2" color="text.secondary" noWrap>{video.artist}</Typography>
                <Typography variant="caption" color="text.secondary">{formatTime(video.duration)}</Typography>
                <Button fullWidth startIcon={<PlayArrowIcon />} onClick={(event) => { event.stopPropagation(); openVideo(video) }} sx={{ mt: 1 }}>
                  Play Fullscreen
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {selectedVideo && (
        <Box ref={playerRef} sx={{ position: 'fixed', inset: 0, zIndex: 1400, bgcolor: '#050505', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 1.5, color: 'white' }}>
            <Typography noWrap sx={{ maxWidth: '80%' }}>{selectedVideo.title}</Typography>
            <IconButton color="inherit" aria-label="Close video player" onClick={closeVideo}><CloseIcon /></IconButton>
          </Box>
          <Box sx={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
            <video
              ref={videoRef}
              src={`${API_BASE_URL}/videos/${selectedVideo.id}/stream`}
              autoPlay
              controls
              style={{ maxWidth: '100%', maxHeight: '100%', width: '100%', height: '100%', objectFit: 'contain' }}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
              onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
              onEnded={() => setIsPlaying(false)}
            />
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, pb: 1.5, color: 'white' }}>
            <IconButton color="inherit" aria-label={isPlaying ? 'Pause video' : 'Play video'} onClick={togglePlay}>
              {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
            <Typography variant="caption">{formatTime(currentTime)}</Typography>
            <Slider aria-label="Video progress" min={0} max={duration || 1} value={Math.min(currentTime, duration || 1)} onChange={(_, value) => { const next = Array.isArray(value) ? value[0] : value; setCurrentTime(next); if (videoRef.current) videoRef.current.currentTime = next }} sx={{ flex: 1, color: 'white' }} />
            <Typography variant="caption">{formatTime(duration)}</Typography>
            <IconButton color="inherit" aria-label={muted ? 'Unmute video' : 'Mute video'} onClick={() => setMuted((value) => !value)}>
              {muted ? <VolumeOffIcon /> : <VolumeUpIcon />}
            </IconButton>
            <Slider aria-label="Video volume" min={0} max={1} step={0.05} value={muted ? 0 : volume} onChange={(_, value) => { const next = Array.isArray(value) ? value[0] : value; setVolume(next); setMuted(next === 0) }} sx={{ width: 100, color: 'white' }} />
            <Select aria-label="Playback speed" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} size="small" sx={{ color: 'white', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,.5)' }, '.MuiSvgIcon-root': { color: 'white' } }}>
              {[0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => <MenuItem key={value} value={value}>{value}x</MenuItem>)}
            </Select>
            <IconButton color="inherit" aria-label="Fullscreen video" onClick={toggleFullscreen}><FullscreenIcon /></IconButton>
          </Box>
        </Box>
      )}
    </Box>
  )
}
