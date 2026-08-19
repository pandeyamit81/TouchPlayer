import React from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardMedia from '@mui/material/CardMedia'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious'
import SkipNextIcon from '@mui/icons-material/SkipNext'
import TextSnippetIcon from '@mui/icons-material/TextSnippet'
import axios from 'axios'
import usePlayerStore from '../store/playerStore'
import useQueueStore from '../store/queueStore'

export default function NowPlaying() {
  const theme = useTheme()
  const {
    isPlaying,
    isPaused,
    currentTrack,
    queue,
    play,
    pause,
    next,
    previous,
  } = usePlayerStore()
  const { fetchQueue } = useQueueStore()
  const [transcript, setTranscript] = React.useState<{ status: string; text: string | null; error?: string | null }>({
    status: 'not_started',
    text: null,
  })

  React.useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  React.useEffect(() => {
    if (!currentTrack) return
    let active = true
    const loadTranscript = async () => {
      try {
        const response = await axios.get(`/api/v1/music/transcription/${currentTrack.id}`)
        if (active) setTranscript(response.data)
      } catch (error) {
        console.error('Failed to load transcript:', error)
      }
    }
    loadTranscript()
    const interval = setInterval(loadTranscript, 3000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [currentTrack?.id])

  const handleTranscribe = async () => {
    if (!currentTrack) return
    try {
      const response = await axios.post(`/api/v1/music/transcribe/${currentTrack.id}`)
      setTranscript((current) => ({ ...current, status: response.data.status, error: response.data.error }))
    } catch (error) {
      console.error('Failed to queue transcription:', error)
      setTranscript((current) => ({ ...current, status: 'failed', error: 'Unable to queue transcription' }))
    }
  }

  if (!currentTrack) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 48px)' }}>
        <Typography variant="h5" color="text.secondary">
          No track playing
        </Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Now Playing
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardMedia
              component="div"
              sx={{
                height: { xs: 220, sm: 240, md: 400 },
                backgroundColor: theme.palette.background.default,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography variant="h2" color="text.secondary">
                {currentTrack.title.charAt(0)}
              </Typography>
            </CardMedia>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                {currentTrack.title}
              </Typography>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {currentTrack.artist}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {currentTrack.album}
              </Typography>
              <Button
                sx={{ mt: 2 }}
                variant="outlined"
                startIcon={<TextSnippetIcon />}
                onClick={handleTranscribe}
                disabled={transcript.status === 'queued' || transcript.status === 'running'}
              >
                {transcript.status === 'not_started' ? 'Transcribe' : transcript.status}
              </Button>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              {transcript.text && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" gutterBottom>Transcript</Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto' }}>
                    {transcript.text}
                  </Typography>
                </Box>
              )}
              {transcript.error && (
                <Typography variant="body2" color="error" sx={{ mb: 2 }}>
                  {transcript.error}
                </Typography>
              )}
              <Typography variant="h5" gutterBottom>
                Queue ({queue.length} tracks)
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Button
                  onClick={previous}
                  variant="contained"
                  startIcon={<SkipPreviousIcon />}
                >
                  Previous
                </Button>
                
                <Button
                  onClick={isPlaying ? pause : play}
                  variant="contained"
                  color="primary"
                  startIcon={isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                  sx={{ px: 4 }}
                >
                  {isPlaying ? 'Pause' : 'Play'}
                </Button>
                
                <Button
                  onClick={next}
                  variant="contained"
                  endIcon={<SkipNextIcon />}
                >
                  Next
                </Button>
              </Box>
              
              <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                {queue.map((track, index) => (
                  <Box
                    key={track.id}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      p: 1,
                      backgroundColor: index === 0 ? theme.palette.primary.main + '20' : 'transparent',
                      borderRadius: 1,
                    }}
                  >
                    <Typography variant="body2" sx={{ minWidth: 40 }}>
                      {index + 1}
                    </Typography>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        {track.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {track.artist}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {track.duration ? `${Math.floor(track.duration / 60)}:${Math.floor(track.duration % 60).toString().padStart(2, '0')}` : '0:00'}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
