import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App'

// Create theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#35d0c0',
      light: '#7de8dc',
      dark: '#168f87',
      contrastText: '#061317',
    },
    secondary: {
      main: '#ffb454',
      light: '#ffd28e',
      dark: '#cf7921',
    },
    background: {
      default: '#07111a',
      paper: '#10202c',
    },
    text: { primary: '#edf7f5', secondary: '#9bb0b8' },
    divider: 'rgba(173, 218, 214, 0.14)',
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
    h4: { fontSize: '1.35rem', fontWeight: 700, letterSpacing: '0.01em' },
    h5: { fontSize: '1.15rem', fontWeight: 700 },
    h6: { fontSize: '0.95rem', fontWeight: 700 },
    body1: { fontSize: '0.86rem' },
    body2: { fontSize: '0.76rem' },
    button: { fontSize: '0.78rem', fontWeight: 700 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { backgroundColor: '#07111a' },
        body: {
          backgroundColor: '#07111a',
          backgroundImage: 'linear-gradient(135deg, rgba(53,208,192,0.06), transparent 42%), linear-gradient(315deg, rgba(255,180,84,0.04), transparent 55%)',
          minWidth: 320,
          overflowX: 'hidden',
          overscrollBehavior: 'none',
        },
        '#root': { minHeight: '100dvh' },
        'button, a, [role="button"], input, select, textarea': {
          WebkitTapHighlightColor: 'transparent',
        },
        '*::-webkit-scrollbar': {
          width: 8,
          height: 8,
        },
        '*::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '*::-webkit-scrollbar-thumb': {
          backgroundColor: 'rgba(125, 232, 220, 0.28)',
          border: '2px solid transparent',
          borderRadius: 8,
          backgroundClip: 'padding-box',
        },
        '*::-webkit-scrollbar-thumb:hover': {
          backgroundColor: 'rgba(125, 232, 220, 0.52)',
        },
        '*::-webkit-scrollbar-thumb:active': {
          backgroundColor: '#35d0c0',
        },
        '*::-webkit-scrollbar-corner': {
          background: 'transparent',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(8, 22, 32, 0.94)',
          backgroundImage: 'none',
          borderBottom: '1px solid rgba(125, 232, 220, 0.12)',
          boxShadow: '0 5px 20px rgba(0,0,0,0.22)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#0a1822',
          backgroundImage: 'linear-gradient(180deg, rgba(53,208,192,0.08), transparent 42%)',
          borderRight: '1px solid rgba(125, 232, 220, 0.12)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          minHeight: 38,
          borderRadius: 8,
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
      },
    },
    MuiIconButton: { styleOverrides: { root: { minWidth: 40, minHeight: 40 } } },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          border: '1px solid rgba(125, 232, 220, 0.1)',
          backgroundImage: 'linear-gradient(145deg, rgba(255,255,255,0.025), transparent 60%)',
          boxShadow: '0 8px 22px rgba(0,0,0,0.16)',
        },
      },
    },
    MuiCardContent: { styleOverrides: { root: { padding: 14, '&:last-child': { paddingBottom: 14 } } } },
    MuiToolbar: { styleOverrides: { root: { minHeight: '48px !important' } } },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          minHeight: 42,
          margin: '2px 8px',
          borderRadius: 8,
          paddingTop: 6,
          paddingBottom: 6,
          '&.Mui-selected': { boxShadow: 'inset 3px 0 #35d0c0' },
        },
      },
    },
    MuiListItemIcon: { styleOverrides: { root: { minWidth: 38 } } },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiInputBase: { styleOverrides: { root: { fontSize: '0.82rem' } } },
  },
})

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
)
