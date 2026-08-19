import React from 'react'
import { useTheme } from '@mui/material/styles'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import IconButton from '@mui/material/IconButton'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Slider from '@mui/material/Slider'
import VolumeUpIcon from '@mui/icons-material/VolumeUp'
import VolumeDownIcon from '@mui/icons-material/VolumeDown'
import VolumeOffIcon from '@mui/icons-material/VolumeOff'
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import StopIcon from '@mui/icons-material/Stop'
import SkipNextIcon from '@mui/icons-material/SkipNext'
import RepeatIcon from '@mui/icons-material/Repeat'
import ShuffleIcon from '@mui/icons-material/Shuffle'
import QueueMusicIcon from '@mui/icons-material/QueueMusic'
import QueuePlayNextIcon from '@mui/icons-material/QueuePlayNext'
import PlaylistAddIcon from '@mui/icons-material/PlaylistAdd'
import usePlayerStore from '../store/playerStore'
import useQueueStore from '../store/queueStore'
import usePlaylistStore from '../store/playlistStore'

export default function PlayerControls() {
  const theme = useTheme()
  const {
    isPlaying,
    currentTrack,
    volume,
    repeat,
    random,
    elapsed,
    duration,
    play,
    pause,
    stop,
    next,
    previous,
    seek,
    setVolume,
    toggleRepeat,
    toggleRandom,
    syncStatus,
  } = usePlayerStore()
  const { fetchQueue, addToQueueNext } = useQueueStore()
  const { playlists, fetchPlaylists, addTrackToPlaylist } = usePlaylistStore()

  const [displayElapsed, setDisplayElapsed] = React.useState(0)
  const [seeking, setSeeking] = React.useState(false)
  const [premuteVolume, setPremuteVolume] = React.useState(volume)
  const [playlistMenuAnchor, setPlaylistMenuAnchor] = React.useState<null | HTMLElement>(null)

  React.useEffect(() => {
    syncStatus()
    fetchPlaylists()
    const interval = setInterval(syncStatus, 1000)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') syncStatus()
    }
    window.addEventListener('focus', syncStatus)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      clearInterval(interval)
      window.removeEventListener('focus', syncStatus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [syncStatus, fetchPlaylists])

  // Reseed the local timer whenever the backend reports a new position.
  React.useEffect(() => {
    if (!seeking) {
      setDisplayElapsed(elapsed)
    }
  }, [elapsed, seeking])

  // Advance the progress bar once per second while playing.
  React.useEffect(() => {
    if (!isPlaying || seeking) return
    const interval = setInterval(() => {
      setDisplayElapsed((prev) => (duration ? Math.min(prev + 1, duration) : prev + 1))
    }, 1000)
    return () => clearInterval(interval)
  }, [isPlaying, seeking, duration])

  const handlePlayPause = () => {
    if (isPlaying) {
      pause()
    } else {
      play()
    }
  }

  const handleVolumeChange = (_event: Event, newValue: number | number[]) => {
    setVolume(newValue as number)
  }

  const handleToggleMute = () => {
    if (volume > 0) {
      setPremuteVolume(volume)
      setVolume(0)
    } else {
      setVolume(premuteVolume > 0 ? premuteVolume : 50)
    }
  }

  const formatTime = (seconds: number) => {
    const total = Math.max(0, Math.floor(seconds))
    const mins = Math.floor(total / 60)
    const secs = total % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleAddToPlaylist = (event: React.MouseEvent<HTMLElement>) => {
    if (currentTrack && playlists.length > 0) {
      setPlaylistMenuAnchor(event.currentTarget)
    }
  }

  if (!currentTrack) {
    return null
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 0,
        left: { xs: 0, sm: '176px' },
        right: 0,
        backgroundColor: theme.palette.background.paper,
        boxShadow: theme.shadows[8],
        px: { xs: 1, sm: 1.5 },
        py: 0.5,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 0.25,
      }}
    >
      {/* Track info */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minHeight: 24 }}>
        <Typography variant="body1" sx={{ fontWeight: 'bold', flex: 1 }}>
          {currentTrack.title}
        </Typography>
        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
          {currentTrack.artist}
        </Typography>
      </Box>

      {/* Progress bar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="caption" sx={{ minWidth: 40 }}>
          {formatTime(displayElapsed)}
        </Typography>
        <Slider
          value={Math.min(displayElapsed, duration || currentTrack.duration || 0)}
          max={duration || currentTrack.duration || 100}
          aria-label="Progress"
          onChange={(_event, newValue) => {
            setSeeking(true)
            setDisplayElapsed(newValue as number)
          }}
          onChangeCommitted={(_event, newValue) => {
            setSeeking(false)
            seek(newValue as number)
          }}
          sx={{
            flex: 1,
            '& .MuiSlider-thumb': {
              width: 12,
              height: 12,
            },
          }}
        />
        <Typography variant="caption" sx={{ minWidth: 40 }}>
          {formatTime(duration || currentTrack.duration || 0)}
        </Typography>
      </Box>

      {/* Controls */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
        <IconButton
          onClick={toggleRandom}
          sx={{ color: random ? theme.palette.primary.main : theme.palette.text.secondary }}
        >
          <ShuffleIcon />
        </IconButton>

        <IconButton onClick={previous}>
          <SkipPreviousIcon sx={{ fontSize: 40 }} />
        </IconButton>

        <IconButton
          onClick={handlePlayPause}
          sx={{
            backgroundColor: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            width: 44,
            height: 44,
            '&:hover': {
              backgroundColor: theme.palette.primary.dark,
            },
          }}
        >
          {isPlaying ? <PauseIcon sx={{ fontSize: 32 }} /> : <PlayArrowIcon sx={{ fontSize: 32 }} />}
        </IconButton>

        <IconButton onClick={next}>
          <SkipNextIcon sx={{ fontSize: 40 }} />
        </IconButton>

        <IconButton onClick={stop} aria-label="Stop">
          <StopIcon sx={{ fontSize: 32 }} />
        </IconButton>

        <IconButton
          onClick={toggleRepeat}
          sx={{ color: repeat ? theme.palette.primary.main : theme.palette.text.secondary }}
        >
          <RepeatIcon />
        </IconButton>
      </Box>

      {/* Volume */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <IconButton onClick={handleToggleMute} aria-label={volume === 0 ? 'Unmute' : 'Mute'}>
          {volume === 0 ? <VolumeOffIcon /> : <VolumeUpIcon />}
        </IconButton>
        <IconButton onClick={() => setVolume(Math.max(0, volume - 10))}>
          <VolumeDownIcon />
        </IconButton>
        <Slider
          value={volume}
          min={0}
          max={100}
          onChange={handleVolumeChange}
          aria-label="Volume"
          sx={{ flex: 1 }}
        />
        <IconButton onClick={() => setVolume(Math.min(100, volume + 10))}>
          <VolumeUpIcon />
        </IconButton>
        <IconButton onClick={fetchQueue}>
          <QueueMusicIcon />
        </IconButton>
        <IconButton
          title="Add current song next"
          aria-label="Add current song next"
          onClick={() => currentTrack && addToQueueNext(currentTrack.id)}
        >
          <QueuePlayNextIcon />
        </IconButton>
        <IconButton
          title="Add current song to playlist"
          aria-label="Add current song to playlist"
          onClick={handleAddToPlaylist}
          disabled={playlists.length === 0}
        >
          <PlaylistAddIcon />
        </IconButton>
        <Menu
          anchorEl={playlistMenuAnchor}
          open={Boolean(playlistMenuAnchor)}
          onClose={() => setPlaylistMenuAnchor(null)}
        >
          {playlists.map((playlist) => (
            <MenuItem
              key={playlist.id}
              onClick={async () => {
                if (currentTrack) {
                  await addTrackToPlaylist(playlist.id, currentTrack.id)
                }
                setPlaylistMenuAnchor(null)
              }}
            >
              {playlist.name}
            </MenuItem>
          ))}
        </Menu>
      </Box>
    </Box>
  )
}
