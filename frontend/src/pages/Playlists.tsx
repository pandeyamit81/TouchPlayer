import React from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import PlaylistPlayIcon from '@mui/icons-material/PlaylistPlay'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Divider from '@mui/material/Divider'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline'
import usePlaylistStore from '../store/playlistStore'
import useLibraryStore from '../store/libraryStore'

export default function Playlists() {
  const theme = useTheme()
  const {
    playlists,
    currentPlaylist,
    isLoading,
    fetchPlaylists,
    fetchPlaylist,
    createPlaylist,
    updatePlaylist,
    deletePlaylist,
    playPlaylist,
    removeTrackFromPlaylist,
  } = usePlaylistStore()
  const { tracks, fetchTracks } = useLibraryStore()
  const [name, setName] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [selectedId, setSelectedId] = React.useState<number | null>(null)
  const [message, setMessage] = React.useState<string | null>(null)
  const [trackIdToAdd, setTrackIdToAdd] = React.useState<number | ''>('')

  React.useEffect(() => {
    fetchPlaylists()
    fetchTracks()
  }, [fetchPlaylists, fetchTracks])

  const handleCreate = async () => {
    const trimmedName = name.trim()
    if (!trimmedName) return
    try {
      await createPlaylist(trimmedName, description.trim() || undefined)
      setName('')
      setDescription('')
      setMessage(`Created ${trimmedName}`)
    } catch {
      setMessage('Could not create playlist')
    }
  }

  const handleSelect = async (id: number) => {
    setSelectedId(id)
    await fetchPlaylist(id)
  }

  const handleRename = async (playlist: { id: number; name: string; description?: string }) => {
    const nextName = window.prompt('Playlist name', playlist.name)?.trim()
    if (!nextName || nextName === playlist.name) return
    await updatePlaylist(playlist.id, nextName, playlist.description)
    if (selectedId === playlist.id) await fetchPlaylist(playlist.id)
  }

  const handleDelete = async (id: number) => {
    await deletePlaylist(id)
    if (selectedId === id) setSelectedId(null)
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Playlists
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 1 }}>
          <TextField
            size="small"
            label="New playlist"
            value={name}
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') handleCreate()
            }}
          />
          <TextField
            size="small"
            label="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate} disabled={!name.trim()}>
            Create Playlist
          </Button>
        </Box>
        <Button variant="outlined" onClick={fetchPlaylists}>
          Refresh
        </Button>
        {message && <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{message}</Typography>}
      </Box>
      
      {isLoading ? (
        <Typography variant="body1" color="text.secondary">
          Loading playlists...
        </Typography>
      ) : (
        <Grid container spacing={2}>
          {playlists.map((playlist) => (
            <Grid item xs={12} sm={6} md={4} key={playlist.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    <PlaylistPlayIcon sx={{ color: theme.palette.info.main, fontSize: 48 }} />
                    <Box>
                      <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
                        {playlist.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {playlist.track_count} tracks
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Button variant="outlined" size="small" onClick={() => playPlaylist(playlist.id)}>
                      Play
                    </Button>
                    <Button variant="text" size="small" startIcon={<EditIcon />} onClick={() => handleRename(playlist)}>
                      Rename
                    </Button>
                    <Button variant="text" color="error" size="small" startIcon={<DeleteIcon />} onClick={() => handleDelete(playlist.id)}>
                      Delete
                    </Button>
                    <Button variant="text" size="small" onClick={() => handleSelect(playlist.id)}>
                      View Tracks
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {currentPlaylist && selectedId === currentPlaylist.id && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6">{currentPlaylist.name}</Typography>
            {currentPlaylist.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {currentPlaylist.description}
              </Typography>
            )}
            <Divider sx={{ mb: 1 }} />
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Select
                size="small"
                displayEmpty
                value={trackIdToAdd}
                onChange={(event) => setTrackIdToAdd(event.target.value as number | '')}
                sx={{ minWidth: 260 }}
              >
                <MenuItem value="">Add a track...</MenuItem>
                {tracks.map((track) => (
                  <MenuItem key={track.id} value={track.id}>
                    {track.title} · {track.artist}
                  </MenuItem>
                ))}
              </Select>
              <Button
                variant="contained"
                disabled={trackIdToAdd === ''}
                onClick={async () => {
                  await usePlaylistStore.getState().addTrackToPlaylist(currentPlaylist.id, trackIdToAdd as number)
                  setTrackIdToAdd('')
                  await fetchPlaylist(currentPlaylist.id)
                  await fetchPlaylists()
                }}
              >
                Add Track
              </Button>
            </Box>
            {currentPlaylist.tracks?.map((track: { id: number; title: string; artist: string }) => (
              <Box key={track.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
                <Typography sx={{ flex: 1 }}>{track.title} · {track.artist}</Typography>
                <Button
                  size="small"
                  color="error"
                  startIcon={<RemoveCircleOutlineIcon />}
                  onClick={async () => {
                    await removeTrackFromPlaylist(currentPlaylist.id, track.id)
                    await fetchPlaylist(currentPlaylist.id)
                  }}
                >
                  Remove
                </Button>
              </Box>
            ))}
            {(!currentPlaylist.tracks || currentPlaylist.tracks.length === 0) && (
              <Typography variant="body2" color="text.secondary">No tracks in this playlist.</Typography>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
