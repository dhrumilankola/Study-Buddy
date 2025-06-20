import { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button, 
  TextField, 
  Typography, 
  Box, 
  Tabs, 
  Tab, 
  Alert,
  Chip,
  Card,
  CardContent,
  LinearProgress,
  IconButton
} from '@mui/material';
import {
  Upload as UploadIcon,
  Description as DocumentIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { uploadDocument, getAvailableDocuments, createChatSession, getDocumentStatus } from '../api';

export default function EnhancedSessionCreator({ 
  open, 
  onClose, 
  onSessionCreated 
}) {
  const [activeTab, setActiveTab] = useState(0);
  const [sessionTitle, setSessionTitle] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (open) {
      fetchAvailableDocuments();
    }
  }, [open]);

  const fetchAvailableDocuments = async () => {
    try {
      const documents = await getAvailableDocuments();
      setAvailableDocuments(documents);
    } catch (err) {
      setError('Failed to load available documents');
    }
  };

  const handleFileUpload = async (files) => {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
      const fileId = Date.now() + Math.random();
      
      // Add file to upload list with pending status
      setUploadedFiles(prev => [...prev, {
        id: fileId,
        file,
        status: 'uploading',
        progress: 0,
        documentId: null,
        error: null
      }]);

      try {
        // Upload file
        const response = await uploadDocument(file);
        
        // Update file status to uploaded
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'processing', 
                progress: 100,
                documentId: response.document?.id,
                processingStatus: response.document?.processing_status || 'processing'
              }
            : f
        ));

        // Start polling for processing status
        if (response.document?.id) {
          pollDocumentStatus(response.document.id, fileId);
        }

      } catch (err) {
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'error', error: err.message }
            : f
        ));
      }
    }
  };

  const pollDocumentStatus = async (documentId, fileId) => {
    const maxAttempts = 30; // 30 seconds max
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getDocumentStatus(documentId);
        
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, processingStatus: status.processing_status }
            : f
        ));

        if (status.processing_status === 'indexed') {
          // Document is ready, add to available documents
          await fetchAvailableDocuments();
          setUploadedFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'ready' }
              : f
          ));
        } else if (status.processing_status === 'error' || status.processing_status === 'failed') {
          setUploadedFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'error', error: 'Processing failed' }
              : f
          ));
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000); // Poll every second
        }
      } catch (err) {
        console.error('Error polling document status:', err);
      }
    };

    poll();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragActive(false);
  };

  const toggleDocumentSelection = (documentId) => {
    setSelectedDocuments(prev => 
      prev.includes(documentId)
        ? prev.filter(id => id !== documentId)
        : [...prev, documentId]
    );
  };

  const handleCreateSession = async () => {
    try {
      setLoading(true);
      const session = await createChatSession(
        sessionTitle || null,
        selectedDocuments,
        null
      );
      
      onSessionCreated(session);
      handleClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSessionTitle('');
    setSelectedDocuments([]);
    setUploadedFiles([]);
    setActiveTab(0);
    setError(null);
    onClose();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'indexed':
        return <CheckCircleIcon color="success" />;
      case 'processing':
        return <RefreshIcon className="animate-spin" color="primary" />;
      case 'error':
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <RefreshIcon color="action" />;
    }
  };

  const readyDocuments = availableDocuments.filter(doc => doc.processing_status === 'indexed');
  const canCreateSession = selectedDocuments.length > 0 || readyDocuments.length === 0;

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '600px' }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          Create New Chat Session
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="Session Title (optional)"
          fullWidth
          variant="outlined"
          value={sessionTitle}
          onChange={(e) => setSessionTitle(e.target.value)}
          sx={{ mb: 3 }}
        />

        <Typography variant="h6" gutterBottom>
          Document Selection
        </Typography>

        <Tabs 
          value={activeTab} 
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{ mb: 2 }}
        >
          <Tab label={`Select Existing (${readyDocuments.length})`} />
          <Tab label="Upload New Documents" />
        </Tabs>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Tab 0: Select Existing Documents */}
        {activeTab === 0 && (
          <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
            {readyDocuments.length === 0 ? (
              <Alert severity="info">
                No processed documents available. Upload some documents first.
              </Alert>
            ) : (
              readyDocuments.map((doc) => (
                <Card 
                  key={doc.id} 
                  variant="outlined" 
                  sx={{ 
                    mb: 1, 
                    cursor: 'pointer',
                    border: selectedDocuments.includes(doc.id) ? 2 : 1,
                    borderColor: selectedDocuments.includes(doc.id) ? 'primary.main' : 'divider'
                  }}
                  onClick={() => toggleDocumentSelection(doc.id)}
                >
                  <CardContent sx={{ py: 1.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <DocumentIcon color="action" />
                      <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                        {doc.original_filename}
                      </Typography>
                      <Chip 
                        label="Ready"
                        size="small"
                        color="success"
                        icon={<CheckCircleIcon />}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {(doc.file_size / 1024).toFixed(1)} KB • {doc.chunk_count} chunks
                    </Typography>
                  </CardContent>
                </Card>
              ))
            )}
          </Box>
        )}

        {/* Tab 1: Upload New Documents */}
        {activeTab === 1 && (
          <Box>
            {/* Upload Area */}
            <Box
              sx={{
                border: 2,
                borderStyle: 'dashed',
                borderColor: dragActive ? 'primary.main' : 'grey.300',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                bgcolor: dragActive ? 'primary.50' : 'grey.50',
                cursor: 'pointer',
                mb: 2
              }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-upload').click()}
            >
              <input
                id="file-upload"
                type="file"
                multiple
                accept=".pdf,.txt,.pptx,.ipynb"
                style={{ display: 'none' }}
                onChange={(e) => handleFileUpload(e.target.files)}
              />
              <UploadIcon sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
              <Typography variant="h6" gutterBottom>
                Drop files here or click to upload
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Supports PDF, TXT, PPTX, and IPYNB files (max 20MB each)
              </Typography>
            </Box>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                {uploadedFiles.map((file) => (
                  <Card key={file.id} variant="outlined" sx={{ mb: 1 }}>
                    <CardContent sx={{ py: 1.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <DocumentIcon color="action" />
                        <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                          {file.file.name}
                        </Typography>
                        {getStatusIcon(file.processingStatus)}
                      </Box>
                      {file.status === 'uploading' && (
                        <LinearProgress sx={{ mt: 1 }} />
                      )}
                      {file.status === 'processing' && (
                        <Typography variant="caption" color="primary">
                          Processing document...
                        </Typography>
                      )}
                      {file.status === 'ready' && (
                        <Typography variant="caption" color="success.main">
                          Ready for use in chat sessions
                        </Typography>
                      )}
                      {file.status === 'error' && (
                        <Typography variant="caption" color="error">
                          {file.error}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Box>
        )}

        {selectedDocuments.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              Selected documents: {selectedDocuments.length}
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button 
          onClick={handleCreateSession} 
          variant="contained"
          disabled={loading || !canCreateSession}
        >
          Create Session
        </Button>
      </DialogActions>
    </Dialog>
  );
}
