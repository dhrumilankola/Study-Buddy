import { useState, useEffect } from 'react';
import { Search, Filter, Upload, FileText, CheckCircle2, AlertCircle, Clock, Loader2, Plus, Check } from 'lucide-react';
import { listDocuments, uploadDocument, getDocumentStatus } from '../api';

export default function DocumentSelector({ 
  selectedDocuments = [], 
  onDocumentSelect, 
  onDocumentDeselect,
  allowUpload = true,
  filterReady = true 
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState(filterReady ? 'indexed' : 'all');
  const [uploadingFiles, setUploadingFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const data = await listDocuments();
      setDocuments(data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (files) => {
    const fileArray = Array.from(files);
    
    for (const file of fileArray) {
      const fileId = Date.now() + Math.random();
      
      // Add file to uploading list
      setUploadingFiles(prev => [...prev, {
        id: fileId,
        file,
        status: 'uploading',
        documentId: null,
        error: null
      }]);

      try {
        // Upload file
        const response = await uploadDocument(file);
        
        // Update file status
        setUploadingFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'processing',
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
        setUploadingFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'error', error: err.message }
            : f
        ));
      }
    }
  };

  const pollDocumentStatus = async (documentId, fileId) => {
    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getDocumentStatus(documentId);
        
        setUploadingFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, processingStatus: status.processing_status }
            : f
        ));

        if (status.processing_status === 'indexed') {
          // Document is ready, refresh list and remove from uploading
          await fetchDocuments();
          setUploadingFiles(prev => prev.filter(f => f.id !== fileId));
        } else if (status.processing_status === 'error' || status.processing_status === 'failed') {
          setUploadingFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { ...f, status: 'error', error: 'Processing failed' }
              : f
          ));
        } else if (attempts < maxAttempts) {
          attempts++;
          setTimeout(poll, 1000);
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

  const isDocumentSelected = (documentId) => {
    return selectedDocuments.some(doc => doc.id === documentId);
  };

  const handleDocumentClick = (document) => {
    if (isDocumentSelected(document.id)) {
      onDocumentDeselect && onDocumentDeselect(document);
    } else {
      onDocumentSelect && onDocumentSelect(document);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'indexed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'error':
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = !searchTerm || 
      doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || doc.processing_status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const readyDocuments = filteredDocuments.filter(doc => doc.processing_status === 'indexed');

  return (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
          >
            <option value="all">All Documents</option>
            <option value="indexed">Ready ({readyDocuments.length})</option>
            <option value="processing">Processing</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Upload Area */}
      {allowUpload && (
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            dragActive 
              ? 'border-primary bg-primary/5' 
              : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          }`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => document.getElementById('document-upload').click()}
        >
          <input
            id="document-upload"
            type="file"
            multiple
            accept=".pdf,.txt,.pptx,.ipynb"
            style={{ display: 'none' }}
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm font-medium">Upload new documents</p>
          <p className="text-xs text-muted-foreground">
            Drop files here or click to browse
          </p>
        </div>
      )}

      {/* Uploading Files */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Uploading Documents</h4>
          {uploadingFiles.map((file) => (
            <div key={file.id} className="flex items-center space-x-3 p-3 border rounded-lg bg-card">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.file.name}</p>
                <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                  {getStatusIcon(file.processingStatus)}
                  <span>
                    {file.status === 'uploading' ? 'Uploading...' :
                     file.status === 'processing' ? 'Processing...' :
                     file.status === 'error' ? file.error : 'Ready'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Document List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-8 w-8 mx-auto mb-2" />
            <p className="text-sm">No documents found</p>
            {searchTerm && (
              <p className="text-xs">Try adjusting your search terms</p>
            )}
          </div>
        ) : (
          filteredDocuments.map((doc) => {
            const isSelected = isDocumentSelected(doc.id);
            const isReady = doc.processing_status === 'indexed';
            
            return (
              <div
                key={doc.id}
                className={`flex items-center space-x-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                  isSelected 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border hover:bg-accent'
                } ${
                  !isReady && filterReady ? 'opacity-60 cursor-not-allowed' : ''
                }`}
                onClick={() => {
                  if (!filterReady || isReady) {
                    handleDocumentClick(doc);
                  }
                }}
              >
                <div className="rounded-lg bg-primary/10 p-2">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                  <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                    {getStatusIcon(doc.processing_status)}
                    <span>{doc.processing_status}</span>
                    {doc.chunk_count > 0 && (
                      <>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                      </>
                    )}
                  </div>
                </div>
                
                <div className={`rounded-full p-1 ${
                  isSelected 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-secondary'
                }`}>
                  {isSelected ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Selection Summary */}
      {selectedDocuments.length > 0 && (
        <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg">
          <p className="text-sm font-medium text-primary">
            {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
          </p>
        </div>
      )}
    </div>
  );
}
