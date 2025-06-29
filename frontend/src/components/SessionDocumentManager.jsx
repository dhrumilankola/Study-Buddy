import { useState, useEffect } from 'react';
import { FileText, Plus, X, Search, CheckCircle2, AlertCircle, Clock, Loader2 } from 'lucide-react';
import { listDocuments, updateChatSession } from '../api';
import DocumentSelector from './DocumentSelector';

export default function SessionDocumentManager({ 
  sessionUuid, 
  sessionDocuments = [], 
  onDocumentsUpdate,
  isOpen,
  onClose 
}) {
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchAvailableDocuments();
    }
  }, [isOpen]);

  const fetchAvailableDocuments = async () => {
    try {
      setLoading(true);
      const documents = await listDocuments();
      setAvailableDocuments(documents);
    } catch (error) {
      console.error('Error fetching available documents:', error);
    } finally {
      setLoading(false);
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

  const isDocumentInSession = (documentId) => {
    return sessionDocuments.some(doc => doc.id === documentId);
  };

  const handleAddDocument = async (document) => {
    if (!sessionUuid || isDocumentInSession(document.id)) return;

    try {
      setUpdating(true);
      const currentDocumentIds = sessionDocuments.map(doc => doc.id);
      const newDocumentIds = [...currentDocumentIds, document.id];
      
      await updateChatSession(sessionUuid, null, newDocumentIds);
      
      if (onDocumentsUpdate) {
        onDocumentsUpdate([...sessionDocuments, document]);
      }
    } catch (error) {
      console.error('Error adding document to session:', error);
    } finally {
      setUpdating(false);
    }
  };

  const handleRemoveDocument = async (documentId) => {
    if (!sessionUuid) return;

    try {
      setUpdating(true);
      const newDocumentIds = sessionDocuments
        .filter(doc => doc.id !== documentId)
        .map(doc => doc.id);
      
      await updateChatSession(sessionUuid, null, newDocumentIds);
      
      if (onDocumentsUpdate) {
        onDocumentsUpdate(sessionDocuments.filter(doc => doc.id !== documentId));
      }
    } catch (error) {
      console.error('Error removing document from session:', error);
    } finally {
      setUpdating(false);
    }
  };

  const filteredDocuments = availableDocuments.filter(doc => {
    const matchesSearch = !searchTerm || 
      doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase());
    
    // Only show indexed documents
    return matchesSearch && doc.processing_status === 'indexed';
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-lg w-full max-w-4xl max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Manage Session Documents</h2>
          <button
            onClick={onClose}
            className="rounded-md p-2 hover:bg-secondary"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex h-[60vh]">
          {/* Current Session Documents */}
          <div className="w-1/2 p-6 border-r">
            <h3 className="text-lg font-medium mb-4">
              Current Documents ({sessionDocuments.length})
            </h3>
            
            {sessionDocuments.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                <FileText className="h-12 w-12 mb-2" />
                <p>No documents in this session</p>
                <p className="text-sm">Add documents from the available list</p>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-96">
                {sessionDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 border rounded-lg bg-card"
                  >
                    <div className="flex items-center space-x-3">
                      <FileText className="h-5 w-5 text-primary" />
                      <div>
                        <p className="font-medium text-sm">{doc.original_filename}</p>
                        <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                          {getStatusIcon(doc.processing_status)}
                          <span>{doc.chunk_count} chunks</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveDocument(doc.id)}
                      disabled={updating}
                      className="rounded-md p-1 hover:bg-destructive/10 text-destructive disabled:opacity-50"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Available Documents */}
          <div className="w-1/2 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">Available Documents</h3>
              {updating && <Loader2 className="h-5 w-5 animate-spin" />}
            </div>

            <DocumentSelector
              selectedDocuments={sessionDocuments}
              onDocumentSelect={handleAddDocument}
              onDocumentDeselect={(doc) => handleRemoveDocument(doc.id)}
              allowUpload={true}
              filterReady={true}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t bg-muted/30">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
