import { useState, useEffect } from 'react';
import { FileText, Trash2, Calendar, FileBox } from 'lucide-react';
import { listDocuments } from '../api';

export default function DocumentList() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
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
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-muted-foreground">Loading documents...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="text-destructive mb-2">{error}</div>
        <button
          onClick={fetchDocuments}
          className="text-sm text-primary hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <FileBox className="h-12 w-12 text-muted-foreground mb-2" />
        <h3 className="text-lg font-semibold">No documents yet</h3>
        <p className="text-muted-foreground">Upload some documents to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Your Documents</h2>
      <div className="grid gap-4">
        {documents.map((doc) => (
          <div
            key={doc.filename}
            className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-center space-x-4">
              <div className="p-2 rounded-md bg-primary/10">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="font-medium">{doc.filename}</h3>
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  <span className="flex items-center">
                    <Calendar className="h-4 w-4 mr-1" />
                    {formatDate(doc.upload_date)}
                  </span>
                  <span>{formatFileSize(doc.size)}</span>
                </div>
              </div>
            </div>
            <button 
              className="p-2 hover:bg-destructive/10 rounded-md group"
              onClick={() => console.log('Delete:', doc.filename)}
            >
              <Trash2 className="h-5 w-5 text-muted-foreground group-hover:text-destructive" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}