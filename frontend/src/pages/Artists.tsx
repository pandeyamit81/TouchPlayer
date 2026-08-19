import React from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import IconButton from '@mui/material/IconButton'
import TextField from '@mui/material/TextField'
import PersonIcon from '@mui/icons-material/Person'
import SearchIcon from '@mui/icons-material/Search'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import QueuePlayNextIcon from '@mui/icons-material/QueuePlayNext'
import axios from 'axios'
import useLibraryStore from '../store/libraryStore'
import usePlayerStore from '../store/playerStore'
import useQueueStore from '../store/queueStore'

const API_BASE_URL = '/api/v1'

interface ArtistTrack {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
  track_number?: number
}

export default function Artists() {
  const theme = useTheme()
  const { artists, isLoadingArtists, fetchArtists } = useLibraryStore()
  const playTrack = usePlayerStore((state) => state.playTrack)
  const addToQueueNext = useQueueStore((state) => state.addToQueueNext)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [searchActive, setSearchActive] = React.useState(false)
  const [selectedArtistId, setSelectedArtistId] = React.useState<number | null>(null)
  const [artistTracks, setArtistTracks] = React.useState<ArtistTrack[]>([])
  const [isLoadingTracks, setIsLoadingTracks] = React.useState(false)

  React.useEffect(() => {
    fetchArtists()
  }, [fetchArtists])

  const handleSearch = async () => {
    const query = searchQuery.trim()
    setSearchActive(Boolean(query))
    await fetchArtists(query ? { search: query, limit: 100 } : {})
  }

  const handleShowAll = async () => {
    setSearchQuery('')
    setSearchActive(false)
    await fetchArtists()
  }

  const handleViewTracks = async (artistId: number, artistName: string) => {
    if (selectedArtistId === artistId) {
      setSelectedArtistId(null)
      return
    }
    setSelectedArtistId(artistId)
    setIsLoadingTracks(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/music`, {
        params: { artist: artistName, limit: 1000 },
      })
      setArtistTracks(response.data.tracks || [])
    } catch (error) {
      console.error('Failed to load artist tracks:', error)
      setArtistTracks([])
    } finally {
      setIsLoadingTracks(false)
    }
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Artists
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 1 }}>
          <TextField
            size="small"
            label="Search artists"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') handleSearch()
            }}
            sx={{ minWidth: 260, flex: 1 }}
          />
          <Button variant="contained" startIcon={<SearchIcon />} onClick={handleSearch}>
            Search
          </Button>
        </Box>
        <Button variant="contained" onClick={searchActive ? handleShowAll : fetchArtists}>
          {searchActive ? 'Show All' : 'Refresh'}
        </Button>
      </Box>
      
      {isLoadingArtists ? (
        <Typography variant="body1" color="text.secondary">
          Loading artists...
        </Typography>
      ) : (
        <Grid container spacing={2}>
          {artists.map((artist) => (
            <Grid item xs={6} sm={4} md={3} lg={2} key={artist.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    <PersonIcon sx={{ color: theme.palette.primary.main, fontSize: 48 }} />
                    <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                      {artist.name}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {artist.track_count} tracks
                  </Typography>
                  <Button
                    size="small"
                    sx={{ mt: 1, display: 'block' }}
                    onPointerUp={(event) => {
                      event.stopPropagation()
                      handleViewTracks(artist.id, artist.name)
                    }}
                  >
                    {selectedArtistId === artist.id ? 'Hide Tracks' : 'View Tracks'}
                  </Button>
                </CardContent>
              </Card>
              {selectedArtistId === artist.id && (
                <Box sx={{ mt: 1, p: 1, border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
                  {isLoadingTracks ? (
                    <Typography variant="body2" color="text.secondary">Loading tracks...</Typography>
                  ) : artistTracks.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No tracks found.</Typography>
                  ) : (
                    artistTracks.map((track) => (
                      <Box key={track.id} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" noWrap>
                            {track.track_number ? `${track.track_number}. ` : ''}{track.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {track.album}
                          </Typography>
                        </Box>
                        <IconButton size="small" aria-label={`Play ${track.title}`} onClick={() => playTrack(track)}>
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" aria-label={`Add ${track.title} next`} onClick={() => addToQueueNext(track.id)}>
                          <QueuePlayNextIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    ))
                  )}
                </Box>
              )}
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  )
}
