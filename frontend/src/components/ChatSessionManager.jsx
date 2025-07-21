import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Stack,
  Divider,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Chat as ChatIcon,
  Forum as ForumIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Description as DocumentIcon,
  AccessTime as TimeIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import EnhancedSessionCreator from './EnhancedSessionCreator';

const ChatSessionManager = ({
  onSessionSelect,
  currentSessionId,
  onNewSession,
  onManageDocuments,
  apiBaseUrl = 'http://localhost:8000/api/v1',
  showHeader = true,
}) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newSessionDialog, setNewSessionDialog] = useState(false);

  // Fetch chat sessions
  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/chat/sessions`);
      if (!response.ok) throw new Error('Failed to fetch sessions');
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle session creation from enhanced dialog
  const handleSessionCreated = async (session) => {
    // Refresh sessions list
    await fetchSessions();

    // Select the new session
    onSessionSelect(session.session_uuid);
    if (onNewSession) onNewSession(session);

    // Close dialog
    setNewSessionDialog(false);
  };

  // Delete session
  const deleteSession = async (sessionUuid) => {
    if (!window.confirm('Are you sure you want to delete this chat session?')) {
      return;
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionUuid}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) throw new Error('Failed to delete session');
      
      // Refresh sessions list
      await fetchSessions();
      
      // If deleted session was current, clear selection
      if (currentSessionId === sessionUuid) {
        onSessionSelect(null);
      }
      
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {showHeader && (
        /* Header */
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" gutterBottom sx={{fontFamily: 'var(--font-sans)', fontWeight: 'var(--font-strong)'}}>
            Chat Sessions
          </Typography>
          <Stack spacing={1}>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setNewSessionDialog(true)}
              fullWidth
              disabled={loading}
              sx={{
                fontFamily: 'var(--font-sans)',
              }}
            >
              New Chat
            </Button>
            {currentSessionId && onManageDocuments && (
              <Button
                variant="outlined"
                startIcon={<DocumentIcon />}
                onClick={() => onManageDocuments(currentSessionId)}
                fullWidth
                size="small"
              >
                Manage Documents
              </Button>
            )}
          </Stack>
        </Box>
      )}

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Sessions List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {loading && sessions.length === 0 ? (
          <Box sx={{ p: 2 }}>
            <Typography color="text.secondary">Loading sessions...</Typography>
          </Box>
        ) : sessions.length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center'}}>
            <Typography sx={{fontFamily: 'var(--font-sans)'}} gutterBottom>
              No chat sessions yet
            </Typography>
            <Typography variant="body2" sx={{fontFamily: 'var(--font-sans)'}}>
              Create your first chat session to get started
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {sessions.map((session) => (
              <ListItem key={session.id} disablePadding>
                <ListItemButton
                  selected={currentSessionId === session.session_uuid}
                  onClick={() => onSessionSelect(session.session_uuid)}
                  sx={{ 
                    flexDirection: 'column', 
                    alignItems: 'stretch',
                    py: 1.5,
                    borderBottom: 1,
                    borderColor: 'divider'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 1 }}>
                    <ForumIcon sx={{ mr: 1, color: 'text.secondary' }} />
                    <Typography 
                      variant="subtitle2" 
                      sx={{ 
                        flex: 1, 
                        fontFamily: 'var(--font-sans)',
                        fontWeight: currentSessionId === session.session_uuid ? 'bold' : 'normal'
                      }}
                      noWrap
                    >
                      {session.title || `Chat ${session.id}`}
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(session.session_uuid);
                      }}
                      sx={{ ml: 1, color: 'var(--input)' }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 1 }}>
                    <TimeIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                    <Typography variant="caption" color="text.secondary" sx={{fontFamily: 'var(--font-sans)'}}>
                      {formatDistanceToNow(new Date(session.last_activity), { addSuffix: true })}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{fontFamily: 'var(--font-sans)'}}>
                      • {session.total_messages} messages
                    </Typography>
                  </Box>
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {/* Enhanced Session Creator */}
      <EnhancedSessionCreator
        open={newSessionDialog}
        onClose={() => setNewSessionDialog(false)}
        onSessionCreated={handleSessionCreated}
      />
    </Box>
  );
};

export default ChatSessionManager;
