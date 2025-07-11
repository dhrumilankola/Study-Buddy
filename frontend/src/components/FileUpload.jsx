import { useState, useCallback } from 'react';
import { Upload, X, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '../api';

export default function FileUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFiles = [...e.dataTransfer.files];
    setFiles(prev => [...prev, ...droppedFiles.map(file => ({
      file,
      status: 'pending',
      error: null,
      progress: 0
    }))]);
  }, []);

  const handleFileChange = (e) => {
    const selectedFiles = [...e.target.files];
    setFiles(prev => [...prev, ...selectedFiles.map(file => ({
      file,
      status: 'pending',
      error: null,
      progress: 0
    }))]);
  };

  const handleUpload = async () => {
    setUploading(true);

    for (let fileObj of files) {
      if (fileObj.status === 'completed') continue;

      try {
        setFiles(prev => prev.map(f =>
          f.file === fileObj.file
            ? { ...f, status: 'uploading', progress: 0 }
            : f
        ));

        const response = await uploadDocument(fileObj.file);

        setFiles(prev => prev.map(f =>
          f.file === fileObj.file
            ? {
                ...f,
                status: 'completed',
                progress: 100,
                documentId: response.document?.id,
                processingStatus: response.document?.processing_status || 'processing'
              }
            : f
        ));
      } catch (error) {
        setFiles(prev => prev.map(f =>
          f.file === fileObj.file
            ? { ...f, status: 'error', error: error.message }
            : f
        ));
      }
    }

    setUploading(false);
  };

  const removeFile = (fileToRemove) => {
    setFiles(prev => prev.filter(f => f.file !== fileToRemove.file));
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      <div
        className={`relative rounded-lg border-2 border-dashed transition-all p-6
          ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
          ${files.length > 0 ? 'pb-24' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          multiple
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={handleFileChange}
          accept=".pdf,.txt,.pptx,.ipynb"
        />
        
        <div className="text-center">
          <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-2 text-sm font-semibold">Drag documents here or click to upload</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Support for PDF, TXT, PPTX, and IPYNB files
          </p>
        </div>

        {files.length > 0 && (
          <div className="absolute bottom-0 left-0 right-0 bg-card border-t rounded-b-lg p-4">
            <div className="space-y-2">
              {files.map((fileObj, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-accent/50 rounded-md"
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <span className="text-sm truncate max-w-[200px]" title={fileObj.file.name}>
                      {fileObj.file.name}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {fileObj.status === 'uploading' && (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        <span className="text-xs text-muted-foreground">Uploading...</span>
                      </div>
                    )}
                    {fileObj.status === 'completed' && (
                      <div className="flex items-center space-x-2">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <span className="text-xs text-green-600">
                          {fileObj.processingStatus === 'processing' ? 'Processing...' : 'Ready'}
                        </span>
                      </div>
                    )}
                    {fileObj.status === 'error' && (
                      <div className="flex items-center space-x-1 text-destructive">
                        <AlertCircle className="h-4 w-4" />
                        <span className="text-xs">{fileObj.error}</span>
                      </div>
                    )}
                    <button
                      onClick={() => removeFile(fileObj)}
                      className="p-1 hover:bg-accent rounded transition-colors"
                    >
                      <X className="h-4 w-4 text-muted-foreground" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <button
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
              className={`mt-3 w-full rounded-md px-3 py-2 text-sm font-medium text-primary-foreground
                ${uploading 
                  ? 'bg-primary/70 cursor-not-allowed' 
                  : 'bg-primary hover:bg-primary/90'
                } transition-colors`}
            >
              {uploading ? (
                <span className="flex items-center justify-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Uploading...</span>
                </span>
              ) : (
                'Upload Files'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}