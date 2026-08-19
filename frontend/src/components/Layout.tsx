import React, { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import useMediaQuery from '@mui/material/useMediaQuery'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import List from '@mui/material/List'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Collapse from '@mui/material/Collapse'
import HomeIcon from '@mui/icons-material/Home'
import MusicNoteIcon from '@mui/icons-material/MusicNote'
import AlbumIcon from '@mui/icons-material/Album'
import PersonIcon from '@mui/icons-material/Person'
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary'
import PlaylistPlayIcon from '@mui/icons-material/PlaylistPlay'
import BluetoothIcon from '@mui/icons-material/Bluetooth'
import WifiIcon from '@mui/icons-material/Wifi'
import SmsIcon from '@mui/icons-material/Sms'
import SettingsIcon from '@mui/icons-material/Settings'
import FolderIcon from '@mui/icons-material/Folder'
import EditNoteIcon from '@mui/icons-material/EditNote'
import CategoryIcon from '@mui/icons-material/Category'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew'
import MenuIcon from '@mui/icons-material/Menu'
import axios from 'axios'
import usePlayerStore from '../store/playerStore'
import useSkinStore from '../store/skinStore'
import useSecretMenuStore from '../store/secretMenuStore'

const drawerWidth = 176

function useTouchScroll() {
  const gesture = React.useRef<{ pointerId: number; lastY: number; dragged: boolean } | null>(null)
  const suppressClick = React.useRef(false)

  const onPointerDown = (event: React.PointerEvent<HTMLElement>) => {
    if (event.pointerType !== 'touch') return
    gesture.current = { pointerId: event.pointerId, lastY: event.clientY, dragged: false }
    suppressClick.current = false
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const onPointerMove = (event: React.PointerEvent<HTMLElement>) => {
    const currentGesture = gesture.current
    if (!currentGesture || currentGesture.pointerId !== event.pointerId) return

    const movement = event.clientY - currentGesture.lastY
    if (!currentGesture.dragged && Math.abs(movement) < 3) return
    currentGesture.dragged = true
    currentGesture.lastY = event.clientY
    event.currentTarget.scrollTop -= movement
    event.preventDefault()
  }

  const endGesture = (event: React.PointerEvent<HTMLElement>) => {
    const currentGesture = gesture.current
    if (!currentGesture || currentGesture.pointerId !== event.pointerId) return
    suppressClick.current = currentGesture.dragged
    gesture.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const onClickCapture = (event: React.MouseEvent<HTMLElement>) => {
    if (!suppressClick.current) return
    event.preventDefault()
    event.stopPropagation()
    suppressClick.current = false
  }

  return {
    onPointerDown,
    onPointerMove,
    onPointerUp: endGesture,
    onPointerCancel: endGesture,
    onClickCapture,
  }
}

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const location = useLocation()
  const currentTrack = usePlayerStore((state) => state.currentTrack)
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [musicMenuOpen, setMusicMenuOpen] = React.useState(location.pathname.startsWith('/library') || location.pathname === '/albums' || location.pathname === '/artists')
  const [powerAction, setPowerAction] = React.useState<'reboot' | 'shutdown' | null>(null)
  const { hasImage, settings, imageVersion, fetchSkin } = useSkinStore()
  const smsEnabled = useSecretMenuStore((state) => state.enabled)
  const smsExpiresAt = useSecretMenuStore((state) => state.expiresAt)
  const enableSms = useSecretMenuStore((state) => state.enable)
  const disableSms = useSecretMenuStore((state) => state.disable)
  const settingsPresses = React.useRef(0)
  const settingsSequenceTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null)
  const drawerScroll = useTouchScroll()
  const mainScroll = useTouchScroll()

  React.useEffect(() => {
    fetchSkin()
  }, [fetchSkin])

  React.useEffect(() => {
    if (!smsEnabled || !smsExpiresAt) return
    const remaining = smsExpiresAt - Date.now()
    if (remaining <= 0) {
      disableSms()
      return
    }
    const timer = setTimeout(disableSms, remaining)
    return () => clearTimeout(timer)
  }, [smsEnabled, smsExpiresAt, disableSms])

  React.useEffect(() => () => {
    if (settingsSequenceTimer.current) clearTimeout(settingsSequenceTimer.current)
  }, [])

  const menuItems = [
    { text: 'Home', icon: <HomeIcon />, path: '/' },
    { text: 'Albums', icon: <AlbumIcon />, path: '/albums' },
    { text: 'Artists', icon: <PersonIcon />, path: '/artists' },
    { text: 'Videos', icon: <VideoLibraryIcon />, path: '/videos' },
    { text: 'Playlists', icon: <PlaylistPlayIcon />, path: '/playlists' },
    { text: 'Bluetooth', icon: <BluetoothIcon />, path: '/bluetooth' },
    { text: 'WiFi', icon: <WifiIcon />, path: '/wifi' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ]

  const musicItems = [
    { text: 'All Music', icon: <MusicNoteIcon />, path: '/library' },
    { text: 'By Folder', icon: <FolderIcon />, path: '/library?view=folder' },
    { text: 'By Album', icon: <AlbumIcon />, path: '/library?view=album' },
    { text: 'By Artist', icon: <PersonIcon />, path: '/library?view=artist' },
    { text: 'By Composer', icon: <EditNoteIcon />, path: '/library?view=composer' },
    { text: 'By Genre', icon: <CategoryIcon />, path: '/library?view=genre' },
  ]

  const isMusicItemSelected = (itemPath: string) => {
    const [path, query] = itemPath.split('?')
    return location.pathname === path && location.search === (query ? `?${query}` : '')
  }

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleSettingsPress = () => {
    settingsPresses.current += 1
    if (settingsSequenceTimer.current) clearTimeout(settingsSequenceTimer.current)
    if (settingsPresses.current >= 5) {
      enableSms()
      settingsPresses.current = 0
    } else {
      settingsSequenceTimer.current = setTimeout(() => {
        settingsPresses.current = 0
      }, 2500)
    }
    if (isMobile) setMobileOpen(false)
  }

  const handlePowerAction = async (action: 'reboot' | 'shutdown') => {
    const label = action === 'reboot' ? 'restart' : 'shut down'
    if (!window.confirm(`Are you sure you want to ${label} the Raspberry Pi?`)) return

    setPowerAction(action)
    try {
      await axios.post(`/api/v1/settings/power/${action}`)
    } catch (error) {
      console.error(`Failed to ${label} Raspberry Pi:`, error)
      setPowerAction(null)
    }
  }

  const drawer = (
    <div>
      <Toolbar sx={{ px: 2, minHeight: '56px !important' }}>
        <Typography variant="h6" noWrap component="div" sx={{ color: theme.palette.primary.light, letterSpacing: '0.04em' }}>
          TOUCHPLAYER
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.filter((item) => item.path === '/').map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              component={NavLink}
              to={item.path}
              selected={location.pathname === item.path}
              onClick={() => {
                if (isMobile) {
                  setMobileOpen(false)
                }
              }}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: theme.palette.primary.main,
                  color: theme.palette.primary.contrastText,
                },
              }}
            >
              <ListItemIcon
                sx={{
                  color: location.pathname === item.path
                    ? theme.palette.primary.contrastText
                    : theme.palette.text.primary,
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
        <ListItem disablePadding>
          <ListItemButton onClick={() => setMusicMenuOpen((open) => !open)}>
            <ListItemIcon><MusicNoteIcon /></ListItemIcon>
            <ListItemText primary="My Music" />
            {musicMenuOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </ListItemButton>
        </ListItem>
        <Collapse in={musicMenuOpen} timeout="auto" unmountOnExit>
          <List component="div" disablePadding>
            {musicItems.map((item) => {
              return (
                <ListItem key={item.text} disablePadding>
                  <ListItemButton
                    component={NavLink}
                    to={item.path}
                    selected={isMusicItemSelected(item.path)}
                    onClick={() => {
                      if (isMobile) setMobileOpen(false)
                    }}
                    sx={{ pl: 4 }}
                  >
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} />
                  </ListItemButton>
                </ListItem>
              )
            })}
          </List>
        </Collapse>
        {menuItems.filter((item) => item.path !== '/' && item.path !== '/albums' && item.path !== '/artists').map((item) => (
          <React.Fragment key={item.text}>
            {smsEnabled && item.path === '/wifi' && (
              <ListItem disablePadding>
                <ListItemButton
                  component={NavLink}
                  to="/sms"
                  selected={location.pathname === '/sms'}
                  onClick={() => {
                    if (isMobile) setMobileOpen(false)
                  }}
                  sx={{
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.primary.main,
                      color: theme.palette.primary.contrastText,
                    },
                  }}
                >
                  <ListItemIcon><SmsIcon /></ListItemIcon>
                  <ListItemText primary="SMS" />
                </ListItemButton>
              </ListItem>
            )}
            <ListItem disablePadding>
              <ListItemButton
                component={NavLink}
                to={item.path}
                selected={location.pathname === item.path}
                onClick={() => {
                  if (item.path === '/settings') {
                    handleSettingsPress()
                  } else if (isMobile) {
                    setMobileOpen(false)
                  }
                }}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.primary.main,
                    color: theme.palette.primary.contrastText,
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: location.pathname === item.path
                      ? theme.palette.primary.contrastText
                      : theme.palette.text.primary,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          </React.Fragment>
        ))}
      </List>
      <Divider />
      <List>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => handlePowerAction('reboot')}
            disabled={powerAction !== null}
          >
            <ListItemIcon>
              <RestartAltIcon />
            </ListItemIcon>
            <ListItemText primary={powerAction === 'reboot' ? 'Restarting...' : 'Restart Raspberry Pi'} />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => handlePowerAction('shutdown')}
            disabled={powerAction !== null}
          >
            <ListItemIcon>
              <PowerSettingsNewIcon />
            </ListItemIcon>
            <ListItemText primary={powerAction === 'shutdown' ? 'Shutting down...' : 'Shut Down Raspberry Pi'} />
          </ListItemButton>
        </ListItem>
      </List>
    </div>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100dvh' }}>
      {hasImage && (
        <>
          <Box
            aria-hidden
            sx={{
              position: 'fixed',
              inset: 0,
              zIndex: -1,
              backgroundImage: `url(/api/v1/skin/image?v=${imageVersion})`,
              backgroundSize: settings.fit === 'repeat' ? 'auto' : settings.fit,
              backgroundRepeat: settings.fit === 'repeat' ? 'repeat' : 'no-repeat',
              backgroundPosition: 'center',
              opacity: settings.opacity,
              filter: `blur(${settings.blur}px) brightness(${settings.brightness})`,
            }}
          />
          <Box
            aria-hidden
            sx={{
              position: 'fixed',
              inset: 0,
              zIndex: -1,
              backgroundColor: settings.overlay_color,
              opacity: settings.overlay_opacity,
            }}
          />
        </>
      )}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            {menuItems.find((item) => item.path === location.pathname)?.text || 'TouchPlayer'}
          </Typography>
        </Toolbar>
      </AppBar>
      
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        {isMobile ? (
          <Drawer
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true,
            }}
            sx={{
              display: { xs: 'block', sm: 'none' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
                overflowY: 'auto',
                touchAction: 'none',
                userSelect: 'none',
                overscrollBehaviorY: 'contain',
                WebkitOverflowScrolling: 'touch',
              },
            }}
            PaperProps={drawerScroll}
          >
            {drawer}
          </Drawer>
        ) : (
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: 'none', sm: 'block' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
                height: '100vh',
                overflowY: 'auto',
                touchAction: 'none',
                userSelect: 'none',
                overscrollBehaviorY: 'contain',
                WebkitOverflowScrolling: 'touch',
              },
            }}
            PaperProps={drawerScroll}
            open
          >
            {drawer}
          </Drawer>
        )}
      </Box>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 1.5, sm: 2 },
          pb: { xs: 1.5, sm: 2, md: currentTrack ? '180px' : 2 },
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: {
            xs: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            sm: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            md: 'calc(100vh - 48px)',
          },
          height: {
            xs: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            sm: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            md: 'auto',
          },
          maxHeight: {
            xs: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            sm: currentTrack ? 'calc(100vh - 184px)' : 'calc(100vh - 48px)',
            md: 'none',
          },
          overflowY: { xs: 'auto', sm: 'auto', md: 'visible' },
          overflowX: 'hidden',
          touchAction: 'none',
          userSelect: 'none',
          overscrollBehaviorY: { xs: 'contain', sm: 'contain', md: 'auto' },
          WebkitOverflowScrolling: 'touch',
          boxSizing: 'border-box',
        }}
        {...mainScroll}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  )
}
