import React from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import Button from '@mui/material/Button'
import IconButton from '@mui/material/IconButton'
import TextField from '@mui/material/TextField'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import SearchIcon from '@mui/icons-material/Search'
import MusicNoteIcon from '@mui/icons-material/MusicNote'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PlaylistAddIcon from '@mui/icons-material/PlaylistAdd'
import QueuePlayNextIcon from '@mui/icons-material/QueuePlayNext'
import TextSnippetIcon from '@mui/icons-material/TextSnippet'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import ViewListIcon from '@mui/icons-material/ViewList'
import GridViewIcon from '@mui/icons-material/GridView'
import useLibraryStore from '../store/libraryStore'
import usePlayerStore from '../store/playerStore'
import usePlaylistStore from '../store/playlistStore'
import useQueueStore from '../store/queueStore'
import axios from 'axios'

const API_BASE_URL = '/api/v1'

interface SearchAlbum {
  id: number
  name: string
  artist: string
  track_count: number
}

interface LyricMatch {
  track_id: number | null
  title: string
  file: string
}

export default function Library() {
  const theme = useTheme()
  const [searchParams, setSearchParams] = useSearchParams()
  const libraryView = searchParams.get('view') || 'all'
  const selectedFolder = searchParams.get('folder') || ''
  const { tracks, isLoadingTracks, fetchTracks } = useLibraryStore()
  const playTrack = usePlayerStore((state) => state.playTrack)
  const { playlists, fetchPlaylists, addTrackToPlaylist } = usePlaylistStore()
  const addToQueueNext = useQueueStore((state) => state.addToQueueNext)
  const [searchQuery, setSearchQuery] = React.useState('')
  const [deepSearch, setDeepSearch] = React.useState(false)
  const [searching, setSearching] = React.useState(false)
  const [searchPerformed, setSearchPerformed] = React.useState(false)
  const [searchAlbums, setSearchAlbums] = React.useState<SearchAlbum[]>([])
  const [lyricMatches, setLyricMatches] = React.useState<LyricMatch[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = React.useState<number | ''>('')
  const [transcriptionStatus, setTranscriptionStatus] = React.useState<Record<number, string>>({})
  const [enrichmentStatus, setEnrichmentStatus] = React.useState<Record<number, string>>({})
  const [batchEnrichmentStatus, setBatchEnrichmentStatus] = React.useState('')
  const [layout, setLayout] = React.useState<'grid' | 'list'>('grid')

  React.useEffect(() => {
    fetchTracks({ limit: 1000 })
    fetchPlaylists()
  }, [fetchTracks, fetchPlaylists])

  const handleSearch = async () => {
    const query = searchQuery.trim()
    if (!query) {
      setSearchPerformed(false)
      setSearchAlbums([])
      setLyricMatches([])
      await fetchTracks({ limit: 1000 })
      return
    }

    setSearching(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/music/search`, {
        params: { query, deep: deepSearch, limit: 100 },
      })
      useLibraryStore.setState({ tracks: response.data.tracks || [] })
      setSearchAlbums(response.data.albums || [])
      setLyricMatches(response.data.lyric_matches || [])
      setSearchPerformed(true)
    } catch (error) {
      console.error('Failed to search music:', error)
    } finally {
      setSearching(false)
    }
  }

  const handleShowAll = async () => {
    setSearchPerformed(false)
    setSearchAlbums([])
    setLyricMatches([])
    await fetchTracks({ limit: 1000 })
  }

  const handleTranscribe = async (trackId: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/music/transcribe/${trackId}`)
      setTranscriptionStatus((current) => ({ ...current, [trackId]: response.data.status }))
    } catch (error) {
      console.error('Failed to queue transcription:', error)
      setTranscriptionStatus((current) => ({ ...current, [trackId]: 'failed' }))
    }
  }

  const handleEnrich = async (trackId: number) => {
    setEnrichmentStatus((current) => ({ ...current, [trackId]: 'updating' }))
    try {
      const response = await axios.post(`${API_BASE_URL}/music/enrich/${trackId}`)
      if (response.data.matched) {
        const metadata = response.data.metadata || {}
        useLibraryStore.setState((state) => ({
          tracks: state.tracks.map((track) => track.id === trackId
            ? {
                ...track,
                artist: metadata.artist || track.artist,
                album: metadata.album || track.album,
                genre: metadata.genre || track.genre,
                year: metadata.year || track.year,
              }
            : track),
        }))
        setEnrichmentStatus((current) => ({ ...current, [trackId]: 'updated' }))
      } else {
        setEnrichmentStatus((current) => ({ ...current, [trackId]: 'no match' }))
      }
    } catch (error: any) {
      console.error('Failed to enrich track metadata:', error)
      const status = error?.response?.status === 503 ? 'offline' : 'failed'
      setEnrichmentStatus((current) => ({ ...current, [trackId]: status }))
    }
  }

  const handleBatchEnrich = async () => {
    setBatchEnrichmentStatus('Starting...')
    try {
      const response = await axios.post(`${API_BASE_URL}/music/enrich-missing`, null, { params: { limit: 25 } })
      setBatchEnrichmentStatus(response.data.queued
        ? `Queued ${response.data.queued} tracks`
        : 'All metadata complete')
      if (response.data.queued) {
        setTimeout(() => fetchTracks(), 5000)
      }
    } catch (error: any) {
      setBatchEnrichmentStatus(error?.response?.status === 409 ? 'Batch already running' : 'offline/error')
    }
  }

  React.useEffect(() => {
    const activeIds = Object.entries(transcriptionStatus)
      .filter(([, status]) => status === 'queued' || status === 'running')
      .map(([trackId]) => Number(trackId))
    if (activeIds.length === 0) return
    const interval = setInterval(() => {
      activeIds.forEach(async (trackId) => {
        try {
          const response = await axios.get(`${API_BASE_URL}/music/transcription/${trackId}`)
          setTranscriptionStatus((current) => ({ ...current, [trackId]: response.data.status }))
        } catch (error) {
          console.error('Failed to check transcription:', error)
        }
      })
    }, 3000)
    return () => clearInterval(interval)
  }, [transcriptionStatus])

  const viewLabels: Record<string, string> = {
    all: 'All Music',
    folder: 'By Folder',
    album: 'By Album',
    artist: 'By Artist',
    composer: 'By Composer',
    genre: 'By Genre',
  }
  const getTrackGroup = (track: typeof tracks[number]) => {
    if (libraryView === 'folder') {
      const parts = track.file_path.split('/')
      return parts.length > 1 ? parts.slice(0, -1).join('/') || '/' : 'Music'
    }
    if (libraryView === 'album') return track.album || 'Unknown Album'
    if (libraryView === 'artist') return track.artist || 'Unknown Artist'
    if (libraryView === 'genre') return track.genre || 'Unknown Genre'
    return ''
  }
  const groupedTracks = tracks.reduce<Record<string, typeof tracks>>((groups, track) => {
    const group = getTrackGroup(track)
    if (!group) return groups
    groups[group] = groups[group] || []
    groups[group].push(track)
    return groups
  }, {})
  const visibleTracks = libraryView === 'folder'
    ? (selectedFolder ? groupedTracks[selectedFolder] || [] : [])
    : tracks

  const selectFolder = (folder: string) => {
    setSearchParams({ view: 'folder', folder })
  }

  const clearFolder = () => {
    setSearchParams({ view: 'folder' })
  }

  const renderTrack = (track: typeof tracks[number]) => (
    <Box
      key={track.id}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        p: layout === 'list' ? 1 : 0,
        borderBottom: layout === 'list' ? `1px solid ${theme.palette.divider}` : 'none',
      }}
    >
      <MusicNoteIcon sx={{ color: theme.palette.primary.main, flexShrink: 0 }} />
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body1" sx={{ fontWeight: 'bold' }} noWrap>{track.title}</Typography>
        <Typography variant="body2" color="text.secondary" noWrap>{track.artist} · {track.album}</Typography>
        <Typography variant="caption" color="text.secondary">
          {track.duration ? `${Math.floor(track.duration / 60)}:${Math.floor(track.duration % 60).toString().padStart(2, '0')}` : '0:00'}
        </Typography>
      </Box>
      <IconButton color="primary" aria-label={`Play ${track.title}`} onClick={() => playTrack(track)}><PlayArrowIcon /></IconButton>
      <IconButton title="Add to queue next" aria-label={`Add ${track.title} next`} onClick={() => addToQueueNext(track.id)}><QueuePlayNextIcon /></IconButton>
      <IconButton
        title="Add to selected playlist"
        aria-label={`Add ${track.title} to playlist`}
        disabled={selectedPlaylistId === ''}
        onClick={() => addTrackToPlaylist(selectedPlaylistId as number, track.id)}
      >
        <PlaylistAddIcon />
      </IconButton>
      {layout === 'list' && (
        <>
          <Button size="small" startIcon={<TextSnippetIcon />} onClick={() => handleTranscribe(track.id)} disabled={transcriptionStatus[track.id] === 'queued' || transcriptionStatus[track.id] === 'running'}>
            {transcriptionStatus[track.id] || 'Transcribe'}
          </Button>
          <Button size="small" startIcon={<AutoAwesomeIcon />} onClick={() => handleEnrich(track.id)} disabled={enrichmentStatus[track.id] === 'updating'}>
            {enrichmentStatus[track.id] || 'Find Metadata'}
          </Button>
        </>
      )}
    </Box>
  )

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        {viewLabels[libraryView] || 'Music Library'}
      </Typography>

      {libraryView !== 'all' && (
        <Box sx={{ mb: 2 }}>
          {libraryView === 'composer' ? (
            <Typography variant="body2" color="text.secondary">
              Composer metadata is not indexed for the current library. Showing all tracks until the library scanner includes composer tags.
            </Typography>
          ) : (
            <Grid container spacing={1}>
              {Object.entries(groupedTracks).map(([group, groupItems]) => (
                <Grid item xs={12} sm={6} md={4} key={group}>
                  <Card variant="outlined" sx={{ borderColor: selectedFolder === group ? 'primary.main' : undefined }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Button
                        fullWidth
                        color={selectedFolder === group ? 'primary' : 'inherit'}
                        onClick={() => libraryView === 'folder' ? selectFolder(group) : undefined}
                        sx={{ justifyContent: 'flex-start', textAlign: 'left', p: 0, textTransform: 'none' }}
                      >
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{group}</Typography>
                      </Button>
                      <Typography variant="caption" color="text.secondary">{groupItems.length} tracks</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      )}
      
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap', mb: 1 }}>
          <TextField
            size="small"
            label="Search songs, albums, lyrics"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') handleSearch()
            }}
            sx={{ minWidth: 280, flex: 1 }}
          />
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={handleSearch}
            disabled={searching}
          >
            {searching ? 'Searching...' : 'Search'}
          </Button>
          <FormControlLabel
            control={<Checkbox checked={deepSearch} onChange={(event) => setDeepSearch(event.target.checked)} />}
            label="Deep Search"
          />
        </Box>
        <Button variant="contained" onClick={searchPerformed ? handleShowAll : fetchTracks}>
          {searchPerformed ? 'Show All' : 'Refresh'}
        </Button>
        {libraryView === 'all' && (
          <Button variant="outlined" onClick={handleBatchEnrich} disabled={batchEnrichmentStatus === 'Starting...'} sx={{ ml: 1, mt: { xs: 1, sm: 0 } }}>
            Find Metadata for All
          </Button>
        )}
          <ToggleButtonGroup
            exclusive
            size="small"
            value={layout}
            onChange={(_, nextLayout) => nextLayout && setLayout(nextLayout)}
            sx={{ ml: { sm: 1 }, mt: { xs: 1, sm: 0 } }}
          >
            <ToggleButton value="list" aria-label="List view"><ViewListIcon /></ToggleButton>
            <ToggleButton value="grid" aria-label="Grid view"><GridViewIcon /></ToggleButton>
          </ToggleButtonGroup>
        {batchEnrichmentStatus && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            {batchEnrichmentStatus}
          </Typography>
        )}
        <Select
          size="small"
          displayEmpty
          value={selectedPlaylistId}
          onChange={(event) => setSelectedPlaylistId(event.target.value as number | '')}
          sx={{ mt: 1, minWidth: 240 }}
        >
          <MenuItem value="">Choose playlist for track actions...</MenuItem>
          {playlists.map((playlist) => (
            <MenuItem key={playlist.id} value={playlist.id}>{playlist.name}</MenuItem>
          ))}
        </Select>
      </Box>

      {searchPerformed && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Search Results
          </Typography>
          {searchAlbums.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1">Albums</Typography>
              {searchAlbums.map((album) => (
                <Typography key={album.id} variant="body2" color="text.secondary">
                  {album.name} · {album.artist} · {album.track_count} tracks
                </Typography>
              ))}
            </Box>
          )}
          {lyricMatches.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1">Lyrics Matches</Typography>
              {lyricMatches.map((match) => (
                <Typography key={`${match.file}-${match.track_id}`} variant="body2" color="text.secondary">
                  {match.title}
                </Typography>
              ))}
            </Box>
          )}
          {tracks.length === 0 && searchAlbums.length === 0 && lyricMatches.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No matches found.
            </Typography>
          )}
        </Box>
      )}
      
      {isLoadingTracks ? (
        <Typography variant="body1" color="text.secondary">
          Loading tracks...
        </Typography>
      ) : libraryView === 'all' ? (
        layout === 'grid' ? (
          <Grid container spacing={2}>
            {tracks.map((track) => <Grid item xs={12} sm={6} md={4} lg={3} key={track.id}><Card sx={{ height: '100%' }}><CardContent>{renderTrack(track)}</CardContent></Card></Grid>)}
          </Grid>
        ) : <Box sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>{tracks.map(renderTrack)}</Box>
      ) : (
        <Box>
          {libraryView === 'folder' && !selectedFolder ? (
            <Typography variant="body1" color="text.secondary">
              Select a folder above to view its songs.
            </Typography>
          ) : (
            <>
              {libraryView === 'folder' && (
                <Button size="small" onClick={clearFolder} sx={{ mb: 1 }}>
                  Show all folders
                </Button>
              )}
          {Object.entries(libraryView === 'folder' ? { [selectedFolder]: visibleTracks } : groupedTracks).map(([group, groupItems]) => (
            <Box key={group} sx={{ mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 1 }}>{group}</Typography>
              {layout === 'grid' ? (
                <Grid container spacing={2}>
                  {groupItems.map((track) => <Grid item xs={12} sm={6} md={4} lg={3} key={track.id}><Card sx={{ height: '100%' }}><CardContent>{renderTrack(track)}</CardContent></Card></Grid>)}
                </Grid>
              ) : <Box sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>{groupItems.map(renderTrack)}</Box>}
            </Box>
          ))}
            </>
          )}
        </Box>
      )}
    </Box>
  )
}
