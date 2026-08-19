import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import CardMedia from '@mui/material/CardMedia'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import MusicNoteIcon from '@mui/icons-material/MusicNote'
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary'
import PlaylistPlayIcon from '@mui/icons-material/PlaylistPlay'
import BluetoothIcon from '@mui/icons-material/Bluetooth'
import WifiIcon from '@mui/icons-material/Wifi'
import SettingsIcon from '@mui/icons-material/Settings'
import QueuePlayNextIcon from '@mui/icons-material/QueuePlayNext'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import IconButton from '@mui/material/IconButton'
import axios from 'axios'
import useLibraryStore from '../store/libraryStore'
import usePlayerStore from '../store/playerStore'
import useQueueStore from '../store/queueStore'

interface Recommendation {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
  reasons: string[]
}

export default function Home() {
  const theme = useTheme()
  const navigate = useNavigate()
  const { fetchTracks, fetchAlbums, fetchArtists } = useLibraryStore()
  const playTrack = usePlayerStore((state) => state.playTrack)
  const addToQueueNext = useQueueStore((state) => state.addToQueueNext)
  const [recommendations, setRecommendations] = React.useState<Recommendation[]>([])

  React.useEffect(() => {
    fetchTracks()
    fetchAlbums()
    fetchArtists()
  }, [fetchTracks, fetchAlbums, fetchArtists])

  React.useEffect(() => {
    axios.get('/api/v1/recommendations', { params: { limit: 6 } })
      .then((response) => setRecommendations(response.data.recommendations || []))
      .catch((error) => console.error('Failed to load recommendations:', error))
  }, [])

  const cards = [
    {
      title: 'Music',
      icon: <MusicNoteIcon sx={{ fontSize: 48 }} />,
      path: '/library',
      color: theme.palette.primary.main,
    },
    {
      title: 'Videos',
      icon: <VideoLibraryIcon sx={{ fontSize: 48 }} />,
      path: '/videos',
      color: theme.palette.secondary.main,
    },
    {
      title: 'Playlists',
      icon: <PlaylistPlayIcon sx={{ fontSize: 48 }} />,
      path: '/playlists',
      color: theme.palette.info.main,
    },
    {
      title: 'Bluetooth',
      icon: <BluetoothIcon sx={{ fontSize: 48 }} />,
      path: '/bluetooth',
      color: theme.palette.success.main,
    },
    {
      title: 'WiFi',
      icon: <WifiIcon sx={{ fontSize: 48 }} />,
      path: '/wifi',
      color: theme.palette.warning.main,
    },
    {
      title: 'Settings',
      icon: <SettingsIcon sx={{ fontSize: 48 }} />,
      path: '/settings',
      color: theme.palette.error.main,
    },
  ]

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Welcome to TouchPlayer
      </Typography>
      
      <Grid container spacing={3}>
        {cards.map((card) => (
          <Grid item xs={6} sm={4} md={2} key={card.title}>
            <Card
              onClick={() => navigate(card.path)}
              sx={{
                height: '100%',
                cursor: 'pointer',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'scale(1.05)',
                },
              }}
            >
              <CardMedia
                sx={{
                  height: 120,
                  backgroundColor: card.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {card.icon}
              </CardMedia>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {card.title}
                </Typography>
                <Button variant="contained" fullWidth>
                  Open
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {recommendations.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            Recommended for you
          </Typography>
          <Grid container spacing={2}>
            {recommendations.map((track) => (
              <Grid item xs={12} sm={6} md={4} key={track.id}>
                <Card>
                  <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body1" noWrap sx={{ fontWeight: 'bold' }}>
                        {track.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {track.artist} · {track.album}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {track.reasons.join(' · ')}
                      </Typography>
                    </Box>
                    <IconButton aria-label={`Play ${track.title}`} onClick={() => playTrack(track)}>
                      <PlayArrowIcon />
                    </IconButton>
                    <IconButton aria-label={`Add ${track.title} next`} onClick={() => addToQueueNext(track.id)}>
                      <QueuePlayNextIcon />
                    </IconButton>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  )
}
