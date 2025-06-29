import { useState, useEffect } from 'react';
import { FileText, Trash2, Calendar, FileBox, Loader2, RefreshCw, CheckCircle2, AlertCircle, Clock, Plus, Check, Package, HardDrive, Eye } from 'lucide-react';
import { listDocuments, deleteDocument } from '../api';

export default function DocumentList({
  documents: propDocuments,
  onDocumentSelect,
  selectedDocuments = [],
  onRefresh,
  onDelete,
  showHeader = true,
  selectionMode = false,
  showDetailedView = true
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingFiles, setDeletingFiles] = useState(new Set());

  // Use prop documents if provided, otherwise fetch them
  useEffect(() => {
    if (propDocuments) {
      setDocuments(propDocuments);
      setLoading(false);
    } else {
      fetchDocuments();
    }
  }, [propDocuments]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const data = await listDocuments();
      setDocuments(data);
      setError(null);
    } catch (err) {
      setError('Failed to load documents');
      console.error('Error fetching documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (document) => {
    // Ask for confirmation
    if (!window.confirm(`Are you sure you want to delete "${document.original_filename || document.filename}"?`)) {
      return;
    }

    try {
      // Add document ID to deleting set
      const docId = document.id || document.filename;
      setDeletingFiles(prev => new Set(prev).add(docId));

      // Call delete API with document ID
      await deleteDocument(document.id);

      // Remove from documents list
      setDocuments(prev => prev.filter(doc => doc.id !== document.id));

      // Call onRefresh if provided
      if (onRefresh) {
        onRefresh();
      }

      // Show success message (optional)
      console.log(`Successfully deleted ${document.original_filename || document.filename}`);
    } catch (error) {
      console.error('Error deleting document:', error);
      // Show error message
      setError(`Failed to delete ${document.original_filename || document.filename}`);
    } finally {
      // Remove from deleting set
      const docId = document.id || document.filename;
      setDeletingFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(docId);
        return newSet;
      });
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
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

  const getStatusText = (status) => {
    switch (status) {
      case 'indexed':
        return 'Ready';
      case 'processing':
        return 'Processing';
      case 'error':
      case 'failed':
        return 'Error';
      default:
        return 'Pending';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'indexed':
        return 'text-green-600 bg-green-50';
      case 'processing':
        return 'text-blue-600 bg-blue-50';
      case 'error':
      case 'failed':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-yellow-600 bg-yellow-50';
    }
  };

  const handleDocumentSelect = (document) => {
    if (onDocumentSelect) {
      onDocumentSelect(document);
    }
  };

  const isDocumentSelected = (document) => {
    return selectedDocuments.some(selected => selected.id === document.id);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your Documents</h2>
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse rounded-lg border bg-card p-6">
              <div className="h-6 w-3/4 bg-muted rounded mb-4" />
              <div className="space-y-2">
                <div className="h-4 w-1/2 bg-muted rounded" />
                <div className="h-4 w-1/3 bg-muted rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
        <div className="flex flex-col items-center justify-center space-y-2">
          <AlertCircle className="h-6 w-6 text-destructive" />
          <p className="text-sm font-medium text-destructive">{error}</p>
          <button
            onClick={fetchDocuments}
            className="inline-flex items-center space-x-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Try again</span>
          </button>
        </div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border bg-card p-12">
        <FileBox className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold">No documents yet</h3>
        <p className="text-sm text-muted-foreground mt-1">Upload some documents to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showHeader && (
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your Documents</h2>
          <button
            onClick={onRefresh || fetchDocuments}
            className="inline-flex items-center space-x-1 rounded-md bg-secondary px-2 py-1 text-sm hover:bg-secondary/80"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh</span>
          </button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {documents.map((doc) => {
          const docId = doc.id || doc.filename;
          const displayName = doc.original_filename || doc.filename;
          const fileSize = doc.file_size || doc.size;
          const uploadDate = doc.created_at || doc.upload_date;
          const status = doc.processing_status || (doc.processed ? 'indexed' : 'processing');

          const isSelected = isDocumentSelected(doc);
          const isReady = status === 'indexed';

          return (
            <div
              key={docId}
              className={`group relative rounded-lg border bg-card transition-all hover:shadow-md ${
                onDocumentSelect ? 'cursor-pointer' : ''
              } ${
                isSelected ? 'ring-2 ring-primary border-primary' : ''
              } ${
                !isReady && selectionMode ? 'opacity-60' : ''
              }`}
              onClick={() => {
                if (onDocumentSelect && (!selectionMode || isReady)) {
                  handleDocumentSelect(doc);
                }
              }}
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1 min-w-0">
                    <div className={`rounded-lg p-2 ${
                      isReady ? 'bg-green-100 text-green-600' :
                      status === 'processing' ? 'bg-blue-100 text-blue-600' :
                      'bg-red-100 text-red-600'
                    }`}>
                      <FileText className="h-5 w-5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium truncate" title={displayName}>
                        {displayName}
                      </h3>

                      {/* Document metadata */}
                      <div className="flex items-center space-x-3 text-sm text-muted-foreground mt-1">
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(uploadDate)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <HardDrive className="h-3 w-3" />
                          <span>{formatFileSize(fileSize)}</span>
                        </div>
                        <span className="uppercase text-xs font-medium px-1.5 py-0.5 bg-muted rounded">
                          {doc.file_type}
                        </span>
                      </div>

                      {/* Status and chunk info */}
                      <div className="flex items-center space-x-3 mt-2">
                        <div className="flex items-center space-x-1">
                          {getStatusIcon(status)}
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(status)}`}>
                            {getStatusText(status)}
                          </span>
                        </div>

                        {doc.chunk_count > 0 && (
                          <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                            <Package className="h-3 w-3" />
                            <span>{doc.chunk_count} chunks</span>
                          </div>
                        )}

                        {showDetailedView && doc.document_metadata && Object.keys(doc.document_metadata).length > 0 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Could open a metadata viewer
                            }}
                            className="flex items-center space-x-1 text-xs text-muted-foreground hover:text-foreground"
                          >
                            <Eye className="h-3 w-3" />
                            <span>Details</span>
                          </button>
                        )}
                      </div>

                      {/* Processing status details */}
                      {status === 'processing' && (
                        <div className="mt-2">
                          <div className="w-full bg-muted rounded-full h-1.5">
                            <div className="bg-blue-500 h-1.5 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">Processing document...</p>
                        </div>
                      )}

                      {status === 'error' && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
                          Processing failed. Please try uploading again.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    {/* Selection indicator */}
                    {onDocumentSelect && (
                      <div className={`rounded-full p-1.5 transition-colors ${
                        isSelected
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary hover:bg-secondary/80'
                      } ${
                        !isReady && selectionMode ? 'opacity-50 cursor-not-allowed' : ''
                      }`}>
                        {isSelected ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Plus className="h-4 w-4" />
                        )}
                      </div>
                    )}

                    {!selectionMode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onDelete) onDelete(doc);
                        }}
                        disabled={deletingFiles.has(docId)}
                        className="absolute top-4 right-4 z-10 rounded-full p-1.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                        title="Delete document"
                      >
                        {deletingFiles.has(docId) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {showDetailedView && (
                <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                  {/* Additional details for detailed view */}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}