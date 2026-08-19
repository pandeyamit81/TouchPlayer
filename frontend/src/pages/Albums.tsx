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
import SearchIcon from '@mui/icons-material/Search'
import AlbumIcon from '@mui/icons-material/Album'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import QueuePlayNextIcon from '@mui/icons-material/QueuePlayNext'
import axios from 'axios'
import useLibraryStore from '../store/libraryStore'
import usePlayerStore from '../store/playerStore'
import useQueueStore from '../store/queueStore'

const API_BASE_URL = '/api/v1'

interface AlbumTrack {
  id: number
  file_path: string
  title: string
  artist: string
  album: string
  duration: number
  track_number?: number
}

export default function Albums() {
  const theme = useTheme()
  const { albums, isLoadingAlbums, fetchAlbums } = useLibraryStore()
  const playTrack = usePlayerStore((state) => state.playTrack)
  const addToQueueNext = useQueueStore((state) => state.addToQueueNext)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [searchActive, setSearchActive] = React.useState(false)
  const [selectedAlbumId, setSelectedAlbumId] = React.useState<number | null>(null)
  const [albumTracks, setAlbumTracks] = React.useState<AlbumTrack[]>([])
  const [isLoadingTracks, setIsLoadingTracks] = React.useState(false)

  React.useEffect(() => {
    fetchAlbums()
  }, [fetchAlbums])

  const handleSearch = async () => {
    const query = searchQuery.trim()
    setSearchActive(Boolean(query))
    await fetchAlbums(query ? { search: query, limit: 100 } : {})
  }

  const handleShowAll = async () => {
    setSearchQuery('')
    setSearchActive(false)
    await fetchAlbums()
  }

  const handleViewTracks = async (albumId: number, albumName: string, artist: string) => {
    if (selectedAlbumId === albumId) {
      setSelectedAlbumId(null)
      return
    }

    setSelectedAlbumId(albumId)
    setIsLoadingTracks(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/music`, {
        params: { album: albumName, artist, limit: 1000 },
      })
      setAlbumTracks(response.data.tracks || [])
    } catch (error) {
      console.error('Failed to load album tracks:', error)
      setAlbumTracks([])
    } finally {
      setIsLoadingTracks(false)
    }
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Albums
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 1 }}>
          <TextField
            size="small"
            label="Search albums"
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
        <Button variant="contained" onClick={searchActive ? handleShowAll : fetchAlbums}>
          {searchActive ? 'Show All' : 'Refresh'}
        </Button>
      </Box>
      
      {isLoadingAlbums ? (
        <Typography variant="body1" color="text.secondary">
          Loading albums...
        </Typography>
      ) : (
        <Grid container spacing={2}>
          {albums.map((album) => (
            <Grid item xs={6} sm={4} md={3} lg={2} key={album.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    <AlbumIcon sx={{ color: theme.palette.primary.main, fontSize: 48 }} />
                    <Box>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {album.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {album.artist}
                      </Typography>
                    </Box>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {album.track_count} tracks
                  </Typography>
                  <Button
                    size="small"
                    sx={{ mt: 1, display: 'block' }}
                    onPointerUp={(event) => {
                      event.stopPropagation()
                      handleViewTracks(album.id, album.name, album.artist)
                    }}
                  >
                    {selectedAlbumId === album.id ? 'Hide Tracks' : 'View Tracks'}
                  </Button>
                </CardContent>
              </Card>
              {selectedAlbumId === album.id && (
                <Box sx={{ mt: 1, p: 1, border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
                  {isLoadingTracks ? (
                    <Typography variant="body2" color="text.secondary">Loading tracks...</Typography>
                  ) : albumTracks.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">No tracks found.</Typography>
                  ) : (
                    albumTracks.map((track) => (
                      <Box key={track.id} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
                          {track.track_number ? `${track.track_number}. ` : ''}{track.title}
                        </Typography>
                        <IconButton
                          size="small"
                          aria-label={`Play ${track.title}`}
                          onClick={() => playTrack(track)}
                        >
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          aria-label={`Add ${track.title} next`}
                          onClick={() => addToQueueNext(track.id)}
                        >
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
