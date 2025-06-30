import { useState, useEffect } from 'react';
import { X, Upload, File, MessageSquare, Mic, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { createChatSession, startVoiceChat, listDocuments, uploadDocument } from '../api';

export default function EnhancedSessionCreator({ open, onClose, onSessionCreated }) {
  const [sessionTitle, setSessionTitle] = useState('');
  const [sessionType, setSessionType] = useState('text');
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  useEffect(() => {
    if (open) {
      fetchDocuments();
      setSessionTitle('');
      setSessionType('text');
      setSelectedDocuments([]);
      setActiveTab(0);
      setUploadFiles([]);
      setError('');
    }
  }, [open]);

  const fetchDocuments = async () => {
    try {
      const docs = await listDocuments();
      setAvailableDocuments(docs.filter(doc => doc.processing_status === 'indexed'));
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  const handleCreateSession = async () => {
    if (!sessionTitle.trim()) {
      setError('Please enter a session title');
      return;
    }

    try {
      setLoading(true);
      setError('');

      let session;
      if (sessionType === 'voice') {
        session = await startVoiceChat(sessionTitle, selectedDocuments);
      } else {
        session = await createChatSession(sessionTitle, selectedDocuments, null, 'text');
      }

      onSessionCreated({ ...session, session_type: sessionType });
      handleClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSessionTitle('');
    setSessionType('text');
    setSelectedDocuments([]);
    setActiveTab(0);
    setUploadFiles([]);
    setError('');
    setUploadProgress({});
    onClose();
  };

  const toggleDocumentSelection = (docId) => {
    setSelectedDocuments(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    setUploadFiles(prev => [...prev, ...files]);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setUploadFiles(prev => [...prev, ...files]);
  };

  const uploadFile = async (file) => {
    try {
      setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
      const result = await uploadDocument(file);
      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
      return result;
    } catch (err) {
      setUploadProgress(prev => ({ ...prev, [file.name]: -1 }));
      throw err;
    }
  };

  const handleUploadAndAdd = async () => {
    try {
      setLoading(true);
      const uploadPromises = uploadFiles.map(file => uploadFile(file));
      const uploadedDocs = await Promise.all(uploadPromises);
      
      const newDocIds = uploadedDocs.map(doc => doc.id);
      setSelectedDocuments(prev => [...prev, ...newDocIds]);
      setUploadFiles([]);
      setUploadProgress({});
      
      await fetchDocuments();
      setActiveTab(0);
    } catch (err) {
      setError('Some files failed to upload');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  const readyDocuments = availableDocuments.filter(doc => doc.processing_status === 'indexed');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-lg w-full max-w-2xl max-h-[85vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Create New Chat Session</h2>
          <button
            onClick={handleClose}
            className="rounded-md p-2 hover:bg-secondary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(85vh-140px)]">
          <div>
            <label className="block text-sm font-medium mb-2">Session Title</label>
            <input
              type="text"
              value={sessionTitle}
              onChange={(e) => setSessionTitle(e.target.value)}
              placeholder="Enter session title..."
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-3">Session Type</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setSessionType('text')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  sessionType === 'text'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <MessageSquare className="h-6 w-6 mx-auto mb-2" />
                <div className="font-medium">Text Chat</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Traditional text-based conversation
                </div>
              </button>

              <button
                onClick={() => setSessionType('voice')}
                className={`p-4 rounded-lg border-2 transition-all ${
                  sessionType === 'voice'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <Mic className="h-6 w-6 mx-auto mb-2" />
                <div className="font-medium">Voice Chat</div>
                <div className="text-xs text-muted-foreground mt-1">
                  AI-powered voice conversation
                </div>
              </button>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-medium">Documents</label>
              <div className="flex rounded-md overflow-hidden border">
                <button
                  onClick={() => setActiveTab(0)}
                  className={`px-3 py-1 text-xs transition-colors ${
                    activeTab === 0
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  Select ({readyDocuments.length})
                </button>
                <button
                  onClick={() => setActiveTab(1)}
                  className={`px-3 py-1 text-xs transition-colors ${
                    activeTab === 1
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  Upload New
                </button>
              </div>
            </div>

            {activeTab === 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {readyDocuments.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <File className="h-8 w-8 mx-auto mb-2" />
                    <p>No processed documents available</p>
                    <p className="text-xs">Upload documents first</p>
                  </div>
                ) : (
                  readyDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => toggleDocumentSelection(doc.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedDocuments.includes(doc.id)
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-primary/50'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <File className="h-4 w-4 text-primary" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                          <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                            <CheckCircle className="h-3 w-3 text-green-500" />
                            <span>Ready • {doc.chunk_count} chunks</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 1 && (
              <div className="space-y-4">
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                  onDragLeave={() => setDragActive(false)}
                  className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                    dragActive ? 'border-primary bg-primary/10' : 'border-border'
                  }`}
                >
                  <Upload className={`h-8 w-8 mx-auto mb-2 ${dragActive ? 'text-primary' : 'text-muted-foreground'}`} />
                  <p className="text-sm font-medium mb-1">
                    Drop files here or click to browse
                  </p>
                  <p className="text-xs text-muted-foreground">
                    PDF, TXT, PPTX, IPYNB files supported
                  </p>
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.txt,.pptx,.ipynb"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className="inline-block mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-xs cursor-pointer hover:bg-primary/90"
                  >
                    Browse Files
                  </label>
                </div>

                {uploadFiles.length > 0 && (
                  <div className="space-y-2">
                    {uploadFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border rounded">
                        <span className="text-sm truncate">{file.name}</span>
                        <div className="flex items-center space-x-2">
                          {uploadProgress[file.name] === 100 && (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          )}
                          {uploadProgress[file.name] === -1 && (
                            <AlertCircle className="h-4 w-4 text-red-500" />
                          )}
                          <button
                            onClick={() => setUploadFiles(prev => prev.filter((_, i) => i !== index))}
                            className="text-red-500 hover:text-red-700"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                    <button
                      onClick={handleUploadAndAdd}
                      disabled={loading}
                      className="w-full py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 text-sm"
                    >
                      {loading ? 'Uploading...' : `Upload ${uploadFiles.length} file(s)`}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <div className="text-xs text-muted-foreground">
            Selected: {selectedDocuments.length} document(s)
            {sessionType === 'voice' && selectedDocuments.length > 0 && (
              <span className="block mt-1">Documents will be uploaded to ElevenLabs for voice interaction</span>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end p-6 border-t bg-muted/30">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-md hover:bg-secondary mr-3"
          >
            Cancel
          </button>
          <button
            onClick={handleCreateSession}
            disabled={loading || !sessionTitle.trim() || (sessionType === 'voice' && selectedDocuments.length === 0)}
            className="px-6 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-all
              disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : sessionType === 'voice' ? (
              'Create Voice Session'
            ) : (
              'Create Text Session'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}