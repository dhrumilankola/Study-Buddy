import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Chip,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  Alert
} from '@mui/material';
import {
  Description as DocumentIcon,
  Edit as EditIcon,
  Add as AddIcon,
  Remove as RemoveIcon
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

const SessionDocuments = ({ 
  sessionUuid, 
  onDocumentsChange,
  apiBaseUrl = 'http://localhost:8000/api/v1'
}) => {
  const [sessionDocuments, setSessionDocuments] = useState([]);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editDialog, setEditDialog] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState([]);

  // Fetch session documents
  const fetchSessionDocuments = async () => {
    if (!sessionUuid) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionUuid}/documents`);
      if (!response.ok) throw new Error('Failed to fetch session documents');
      const data = await response.json();
      setSessionDocuments(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch available documents
  const fetchAvailableDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/chat/available-documents`);
      if (!response.ok) throw new Error('Failed to fetch available documents');
      const data = await response.json();
      setAvailableDocuments(data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Update session documents
  const updateSessionDocuments = async () => {
    if (!sessionUuid) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionUuid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: selectedDocuments,
        }),
      });
      
      if (!response.ok) throw new Error('Failed to update session documents');
      
      // Refresh session documents
      await fetchSessionDocuments();
      
      // Notify parent component
      if (onDocumentsChange) {
        onDocumentsChange(selectedDocuments);
      }
      
      setEditDialog(false);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Get document status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'INDEXED': return 'success';
      case 'PROCESSING': return 'warning';
      case 'ERROR': return 'error';
      case 'FAILED': return 'error';
      default: return 'default';
    }
  };

  // Open edit dialog
  const openEditDialog = () => {
    setSelectedDocuments(sessionDocuments.map(doc => doc.id));
    setEditDialog(true);
  };

  // Toggle document selection in edit dialog
  const toggleDocumentSelection = (documentId) => {
    setSelectedDocuments(prev => 
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  useEffect(() => {
    fetchSessionDocuments();
    fetchAvailableDocuments();
  }, [sessionUuid]);

  if (!sessionUuid) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary">
          Select a chat session to view its documents
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          Session Documents
        </Typography>
        <Tooltip title="Edit document selection">
          <IconButton onClick={openEditDialog} disabled={loading}>
            <EditIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Documents List */}
      {loading && sessionDocuments.length === 0 ? (
        <Typography color="text.secondary">Loading documents...</Typography>
      ) : sessionDocuments.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 3 }}>
          <DocumentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography color="text.secondary" gutterBottom>
            No documents selected
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This chat session doesn't have any documents associated with it.
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={openEditDialog}
          >
            Add Documents
          </Button>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {sessionDocuments.map((doc) => (
            <Card key={doc.id} variant="outlined">
              <CardContent sx={{ py: 1.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <DocumentIcon color="action" />
                  <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                    {doc.original_filename}
                  </Typography>
                  <Chip 
                    label={doc.processing_status}
                    size="small"
                    color={getStatusColor(doc.processing_status)}
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    {(doc.file_size / 1024).toFixed(1)} KB
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {doc.chunk_count} chunks
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Added {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Edit Documents Dialog */}
      <Dialog 
        open={editDialog} 
        onClose={() => setEditDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Edit Session Documents</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select which documents should be included in this chat session's context
          </Typography>
          
          {availableDocuments.length === 0 ? (
            <Alert severity="info">
              No documents available. Upload some documents first.
            </Alert>
          ) : (
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {availableDocuments.map((doc) => (
                <ListItem 
                  key={doc.id}
                  disabled={doc.processing_status !== 'INDEXED'}
                  sx={{ 
                    border: 1, 
                    borderColor: 'divider', 
                    borderRadius: 1, 
                    mb: 1,
                    opacity: doc.processing_status === 'INDEXED' ? 1 : 0.6
                  }}
                >
                  <Checkbox
                    checked={selectedDocuments.includes(doc.id)}
                    onChange={() => toggleDocumentSelection(doc.id)}
                    disabled={doc.processing_status !== 'INDEXED'}
                  />
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ flex: 1 }}>
                          {doc.original_filename}
                        </Typography>
                        <Chip 
                          label={doc.processing_status}
                          size="small"
                          color={getStatusColor(doc.processing_status)}
                        />
                      </Box>
                    }
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        {(doc.file_size / 1024).toFixed(1)} KB • {doc.chunk_count} chunks
                      </Typography>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
          
          <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
            <Typography variant="body2">
              Selected: {selectedDocuments.length} documents
            </Typography>
            {selectedDocuments.length > 0 && (
              <Typography variant="caption" color="text.secondary">
                Only selected documents will be used for context in this chat session
              </Typography>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(false)}>Cancel</Button>
          <Button 
            onClick={updateSessionDocuments} 
            variant="contained"
            disabled={loading}
          >
            Update Documents
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SessionDocuments;
