import React from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import Divider from '@mui/material/Divider'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import Alert from '@mui/material/Alert'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import IconButton from '@mui/material/IconButton'
import SmsIcon from '@mui/icons-material/Sms'
import RefreshIcon from '@mui/icons-material/Refresh'
import SendIcon from '@mui/icons-material/Send'
import DeleteIcon from '@mui/icons-material/Delete'
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline'
import CloseIcon from '@mui/icons-material/Close'
import axios from 'axios'

const API_BASE_URL = '/api/v1'
const SMS_CONTACTS = ['7007507180', '9119688888', '8090498544', '9415044433']

interface SMSMessage {
  id: number
  modem_status: string
  status: string
  direction: 'received' | 'sent'
  number: string
  date: string
  text: string
  reference?: number | null
}

interface SMSNetworkStatus {
  healthy: boolean
  service: string
  serial_device: string
  serial_available: boolean
  sim_ready?: boolean | null
  signal?: number | null
  signal_quality?: number | null
  registration?: string
  packet_registration?: string
  registered?: boolean | null
  packet_attached?: boolean | null
  operator?: string | null
  apn?: string | null
  ppp_connected: boolean
  ip_addresses: string[]
  modem_error?: string
  message?: string
}

export default function SMS() {
  const [messages, setMessages] = React.useState<SMSMessage[]>([])
  const [number, setNumber] = React.useState(SMS_CONTACTS[0])
  const [inboxFilter, setInboxFilter] = React.useState('all')
  const [selectedIds, setSelectedIds] = React.useState<number[]>([])
  const [text, setText] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [sending, setSending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [notice, setNotice] = React.useState<string | null>(null)
  const [networkStatus, setNetworkStatus] = React.useState<SMSNetworkStatus | null>(null)
  const [networkLoading, setNetworkLoading] = React.useState(false)
  const [networkRestarting, setNetworkRestarting] = React.useState(false)
  const [chatOpen, setChatOpen] = React.useState(false)
  const [chatContact, setChatContact] = React.useState('all')

  const loadNetworkStatus = React.useCallback(async () => {
    setNetworkLoading(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/sms/network`)
      setNetworkStatus(response.data)
    } catch (requestError: any) {
      setNetworkStatus(null)
      setError(requestError?.response?.data?.detail || 'Unable to check cellular network')
    } finally {
      setNetworkLoading(false)
    }
  }, [])

  const loadMessages = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/sms/messages`)
      setMessages(response.data?.messages || [])
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Unable to read SMS messages')
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    loadMessages()
    loadNetworkStatus()
  }, [loadMessages, loadNetworkStatus])

  const restartNetwork = async () => {
    setNetworkRestarting(true)
    setError(null)
    setNotice(null)
    try {
      await axios.post(`${API_BASE_URL}/sms/network/restart`)
      setNotice('Cellular network restart requested')
      await loadNetworkStatus()
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Unable to restart cellular network')
    } finally {
      setNetworkRestarting(false)
    }
  }

  const sendMessage = async () => {
    setSending(true)
    setError(null)
    setNotice(null)
    try {
      await axios.post(`${API_BASE_URL}/sms/messages`, { number, text })
      setText('')
      setNotice('Message sent')
      await loadMessages()
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Unable to send SMS message')
    } finally {
      setSending(false)
    }
  }

  const normalizedNumber = (value: string) => {
    const digits = value.replace(/\D/g, '')
    return digits.startsWith('91') && digits.length === 12 ? digits.slice(2) : digits
  }
  const inboxMessages = messages.filter((message) => message.direction === 'received')
  const sentMessages = messages.filter((message) => message.direction === 'sent')
  const inboxNumbers = Array.from(new Set([
    ...SMS_CONTACTS,
    ...inboxMessages.map((message) => normalizedNumber(message.number)).filter(Boolean),
  ]))
  const filteredMessages = inboxMessages.filter((message) => (
    inboxFilter === 'all' || normalizedNumber(message.number) === inboxFilter
  ))

  const statusColor = (status: string): 'default' | 'success' | 'warning' | 'error' | 'info' => {
    if (status === 'read' || status === 'delivered' || status === 'submitted') return 'success'
    if (status === 'unread') return 'info'
    if (status === 'undelivered') return 'error'
    return 'default'
  }

  const toggleSelected = (messageId: number) => {
    setSelectedIds((current) => current.includes(messageId)
      ? current.filter((id) => id !== messageId)
      : [...current, messageId])
  }

  const openChat = (contact = 'all') => {
    setChatContact(contact)
    setChatOpen(true)
  }

  const deleteSelected = async () => {
    const idsToDelete = selectedIds.filter((messageId) => messageId !== 0)
    if (idsToDelete.length === 0) return
    const previousMessages = messages
    setError(null)
    setNotice(null)
    setMessages((current) => current.filter((message) => !idsToDelete.includes(message.id)))
    setSelectedIds([])
    try {
      const results = await Promise.allSettled(idsToDelete.map((messageId) => (
        axios.delete(`${API_BASE_URL}/sms/messages/${messageId}`)
      )))
      const failedIds = results.flatMap((result, index) => (
        result.status === 'rejected' ? [idsToDelete[index]] : []
      ))
      if (failedIds.length > 0) {
        await loadMessages()
        throw new Error('Some messages could not be deleted')
      }
      setNotice('Selected messages deleted')
    } catch (requestError: any) {
      if (requestError?.message === 'Some messages could not be deleted') {
        setError(requestError.message)
      } else {
        setMessages(previousMessages)
        setSelectedIds(selectedIds)
      }
      setError(requestError?.response?.data?.detail || 'Unable to delete selected messages')
    }
  }

  const deleteAll = async () => {
    if (!window.confirm('Delete all SMS messages from the modem?')) return
    const previousMessages = messages
    setError(null)
    setNotice(null)
    setMessages([])
    setSelectedIds([])
    try {
      await axios.delete(`${API_BASE_URL}/sms/messages`)
      setNotice('All messages deleted')
    } catch (requestError: any) {
      setMessages(previousMessages)
      setError(requestError?.response?.data?.detail || 'Unable to delete all messages')
    }
  }

  const chatMessages = messages.filter((message) => (
    chatContact === 'all' || normalizedNumber(message.number) === chatContact
  ))

  return (
    <Box sx={{ p: 2, maxWidth: 720 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <SmsIcon color="primary" />
        <Typography variant="h4">SMS</Typography>
        <Button
          size="small"
          startIcon={<RefreshIcon />}
          onClick={loadMessages}
          disabled={loading}
          sx={{ ml: 'auto' }}
        >
          Refresh
        </Button>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <NetworkCheckIcon color={networkStatus?.healthy ? 'success' : 'warning'} />
            <Typography variant="h6">Cellular network</Typography>
            <Chip
              size="small"
              color={networkStatus?.healthy ? 'success' : 'error'}
              label={networkStatus?.healthy ? 'Connected' : networkLoading ? 'Checking...' : 'Not connected'}
            />
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={loadNetworkStatus}
              disabled={networkLoading || networkRestarting}
              sx={{ ml: { sm: 'auto' } }}
            >
              Check
            </Button>
            <Button
              size="small"
              color="warning"
              variant="outlined"
              startIcon={<RestartAltIcon />}
              onClick={restartNetwork}
              disabled={networkLoading || networkRestarting || networkStatus?.healthy === true}
            >
              {networkRestarting ? 'Restarting...' : 'Restart network'}
            </Button>
          </Box>
          {networkStatus && (
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 1, mt: 2 }}>
              <Typography variant="body2">Service: {networkStatus.service}</Typography>
              <Typography variant="body2">SIM: {networkStatus.sim_ready == null ? 'Unknown' : networkStatus.sim_ready ? 'Ready' : 'Not ready'}</Typography>
              <Typography variant="body2">Signal: {networkStatus.signal === null || networkStatus.signal === undefined ? 'Unavailable' : `${networkStatus.signal}/31`}</Typography>
              <Typography variant="body2">Registration: {networkStatus.registered == null ? 'Unknown' : networkStatus.registered ? 'Registered' : networkStatus.registration || 'Unknown'}</Typography>
              <Typography variant="body2">Data attached: {networkStatus.packet_attached == null ? 'Unknown' : networkStatus.packet_attached ? 'Yes' : 'No'}</Typography>
              <Typography variant="body2">Operator: {networkStatus.operator || 'Unavailable'}</Typography>
              <Typography variant="body2">APN: {networkStatus.apn || 'Unavailable'}</Typography>
              <Typography variant="body2">UART: {networkStatus.serial_available ? networkStatus.serial_device : 'Unavailable'}</Typography>
              <Typography variant="body2">IP: {networkStatus.ip_addresses.length ? networkStatus.ip_addresses.join(', ') : 'Not assigned'}</Typography>
            </Box>
          )}
          {networkStatus?.modem_error && <Alert severity="warning" sx={{ mt: 1.5 }}>{networkStatus.modem_error}</Alert>}
          {!networkStatus?.healthy && networkStatus?.message && <Alert severity="info" sx={{ mt: 1.5 }}>{networkStatus.message}</Alert>}
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Button
            variant="text"
            startIcon={<ChatBubbleOutlineIcon />}
            onClick={() => openChat()}
            sx={{ alignSelf: 'flex-start', p: 0, minWidth: 0, textTransform: 'none', fontSize: '1.25rem', fontWeight: 600 }}
          >
            Send message
          </Button>
          <FormControl size="small" fullWidth>
            <InputLabel id="sms-recipient-label">Recipient</InputLabel>
            <Select
              labelId="sms-recipient-label"
              value={number}
              label="Recipient"
              onChange={(event) => setNumber(event.target.value)}
            >
              {SMS_CONTACTS.map((contact) => (
                <MenuItem key={contact} value={contact}>{contact}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Message"
            value={text}
            onChange={(event) => setText(event.target.value)}
            multiline
            minRows={2}
            maxRows={5}
            inputProps={{ maxLength: 1600 }}
            fullWidth
          />
          <Button
            variant="contained"
            startIcon={<SendIcon />}
            onClick={sendMessage}
            disabled={sending || !number.trim() || !text.trim()}
            sx={{ alignSelf: 'flex-start' }}
          >
            {sending ? 'Sending...' : 'Send SMS'}
          </Button>
        </CardContent>
      </Card>

      {notice && <Typography color="success.main" sx={{ mb: 1 }}>{notice}</Typography>}
      {error && <Typography color="error" sx={{ mb: 1 }}>{error}</Typography>}

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
            <Button
              variant="text"
              startIcon={<ChatBubbleOutlineIcon />}
              onClick={() => openChat()}
              sx={{ p: 0, minWidth: 0, textTransform: 'none', color: 'inherit', fontSize: '1.25rem', fontWeight: 600 }}
            >
              Inbox
            </Button>
            <FormControl size="small" sx={{ minWidth: 180, ml: { sm: 'auto' } }}>
              <InputLabel id="sms-inbox-filter-label">From</InputLabel>
              <Select
                labelId="sms-inbox-filter-label"
                value={inboxFilter}
                label="From"
                onChange={(event) => {
                  setInboxFilter(event.target.value)
                  setSelectedIds([])
                }}
              >
                <MenuItem value="all">All numbers</MenuItem>
                {inboxNumbers.map((contact) => (
                  <MenuItem key={contact} value={contact}>{contact}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
            <Button
              size="small"
              color="error"
              variant="outlined"
              startIcon={<DeleteIcon />}
              onClick={deleteSelected}
              disabled={selectedIds.length === 0}
            >
              Delete Selected
            </Button>
            <Button
              size="small"
              color="error"
              variant="outlined"
              startIcon={<DeleteIcon />}
              onClick={deleteAll}
              disabled={messages.length === 0}
            >
              Delete All
            </Button>
          </Box>
          {filteredMessages.length === 0 && !loading && (
            <Typography color="text.secondary">No received messages found.</Typography>
          )}
          {filteredMessages.map((message, index) => (
            <React.Fragment key={`${message.id}-${message.number}-${index}`}>
              {index > 0 && <Divider sx={{ my: 1.5 }} />}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                <Checkbox
                  checked={selectedIds.includes(message.id)}
                  onChange={() => toggleSelected(message.id)}
                  disabled={message.id < 0}
                  inputProps={{ 'aria-label': `Select message from ${message.number}` }}
                />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {message.number}
                  </Typography>
                  <Chip size="small" color={statusColor(message.status)} label={message.status} sx={{ mt: 0.5 }} />
                  <Typography variant="caption" color="text.secondary">{message.date}</Typography>
                  <Typography sx={{ whiteSpace: 'pre-wrap', mt: 0.5 }}>{message.text}</Typography>
                </Box>
              </Box>
            </React.Fragment>
          ))}
        </CardContent>
      </Card>

      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Button
            variant="text"
            startIcon={<ChatBubbleOutlineIcon />}
            onClick={() => openChat()}
            sx={{ p: 0, minWidth: 0, textTransform: 'none', color: 'inherit', fontSize: '1.25rem', fontWeight: 600, mb: 1 }}
          >
            Sent
          </Button>
          {sentMessages.length === 0 && !loading && (
            <Typography color="text.secondary">No sent messages found.</Typography>
          )}
          {sentMessages.map((message, index) => (
            <React.Fragment key={`${message.id}-${message.number}-sent-${index}`}>
              {index > 0 && <Divider sx={{ my: 1.5 }} />}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                <Checkbox
                  checked={selectedIds.includes(message.id)}
                  onChange={() => toggleSelected(message.id)}
                  disabled={message.id === 0}
                  inputProps={{ 'aria-label': `Select sent message to ${message.number}` }}
                />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    To {message.number}
                  </Typography>
                  <Chip size="small" color={statusColor(message.status)} label={message.status} sx={{ mt: 0.5 }} />
                  {message.date && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>{message.date}</Typography>
                  )}
                  <Typography sx={{ whiteSpace: 'pre-wrap', mt: 0.5 }}>{message.text}</Typography>
                </Box>
              </Box>
            </React.Fragment>
          ))}
        </CardContent>
      </Card>

      <Dialog
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        fullWidth
        maxWidth="sm"
        PaperProps={{ sx: { height: { xs: '88vh', sm: 680 }, bgcolor: '#111b21' } }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: '#e9edef', py: 1.5 }}>
          <ChatBubbleOutlineIcon color="primary" />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6">Messages</Typography>
            <Typography variant="caption" sx={{ color: '#8696a0' }}>
              {chatContact === 'all' ? 'All conversations' : chatContact}
            </Typography>
          </Box>
          <IconButton aria-label="Close chat" onClick={() => setChatOpen(false)} sx={{ color: '#8696a0' }}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, bgcolor: '#e5ddd5', color: '#111b21' }}>
          <Box
            sx={{
              minHeight: '100%',
              p: { xs: 1.5, sm: 2 },
              backgroundImage: 'linear-gradient(rgba(229, 221, 213, 0.92), rgba(229, 221, 213, 0.92)), repeating-linear-gradient(45deg, rgba(17, 27, 33, 0.035) 0, rgba(17, 27, 33, 0.035) 1px, transparent 1px, transparent 9px)',
            }}
          >
            {chatMessages.length === 0 && (
              <Typography sx={{ textAlign: 'center', color: '#667781', mt: 4 }}>
                No messages in this conversation.
              </Typography>
            )}
            {chatMessages.map((message, index) => {
              const outgoing = message.direction === 'sent'
              return (
                <Box key={`${message.id}-${message.number}-chat-${index}`} sx={{ display: 'flex', justifyContent: outgoing ? 'flex-end' : 'flex-start', mb: 1 }}>
                  <Box
                    sx={{
                      maxWidth: '82%',
                      px: 1.5,
                      py: 0.8,
                      bgcolor: outgoing ? '#d9fdd3' : '#ffffff',
                      borderRadius: outgoing ? '10px 3px 10px 10px' : '3px 10px 10px 10px',
                      boxShadow: '0 1px 1px rgba(0, 0, 0, 0.16)',
                    }}
                  >
                    <Typography variant="caption" sx={{ display: 'block', color: '#667781', fontWeight: 600, mb: 0.25 }}>
                      {outgoing ? `To ${normalizedNumber(message.number)}` : `From ${normalizedNumber(message.number)}`}
                    </Typography>
                    <Typography sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{message.text}</Typography>
                    <Typography variant="caption" sx={{ display: 'block', textAlign: 'right', color: '#667781', mt: 0.35 }}>
                      {message.date || (message.status === 'submitted' ? 'Submitted' : message.status)}
                    </Typography>
                  </Box>
                </Box>
              )
            })}
          </Box>
        </DialogContent>
        <DialogActions sx={{ bgcolor: '#111b21', justifyContent: 'space-between', px: 2 }}>
          <Select
            size="small"
            value={chatContact}
            onChange={(event) => setChatContact(event.target.value)}
            sx={{ color: '#e9edef', minWidth: 150, '.MuiOutlinedInput-notchedOutline': { borderColor: '#52616b' }, '.MuiSvgIcon-root': { color: '#8696a0' } }}
            aria-label="Chat contact"
          >
            <MenuItem value="all">All conversations</MenuItem>
            {inboxNumbers.map((contact) => <MenuItem key={contact} value={contact}>{contact}</MenuItem>)}
          </Select>
          <Button onClick={() => setChatOpen(false)} variant="contained">Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
