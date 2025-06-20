import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, RefreshCw, Search, Filter, Plus, Calendar, HardDrive, Package } from 'lucide-react';
import FileUpload from './FileUpload';
import DocumentList from './DocumentList';
import { listDocuments, getAvailableDocuments, getDocumentStatus } from '../api';

export default function DocumentManager({ onDocumentSelect, selectedDocuments = [], showUploadTab = true }) {
  const [activeTab, setActiveTab] = useState(showUploadTab ? 'upload' : 'manage');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [refreshKey, setRefreshKey] = useState(0);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    if (activeTab === 'manage') {
      fetchDocuments();
    }
  }, [activeTab, refreshKey]);

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

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleUploadComplete = () => {
    // Refresh documents list after upload
    if (activeTab === 'manage') {
      handleRefresh();
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const filteredAndSortedDocuments = documents
    .filter(doc => {
      const matchesSearch = !searchTerm ||
        (doc.original_filename || doc.filename).toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus = statusFilter === 'all' ||
        (doc.processing_status || (doc.processed ? 'indexed' : 'processing')) === statusFilter;

      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      let aValue, bValue;

      switch (sortBy) {
        case 'name':
          aValue = (a.original_filename || a.filename).toLowerCase();
          bValue = (b.original_filename || b.filename).toLowerCase();
          break;
        case 'size':
          aValue = a.file_size || a.size || 0;
          bValue = b.file_size || b.size || 0;
          break;
        case 'status':
          aValue = a.processing_status || (a.processed ? 'indexed' : 'processing');
          bValue = b.processing_status || (b.processed ? 'indexed' : 'processing');
          break;
        case 'created_at':
        default:
          aValue = new Date(a.created_at || a.upload_date);
          bValue = new Date(b.created_at || b.upload_date);
          break;
      }

      if (sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

  const getStatusCounts = () => {
    const counts = {
      all: documents.length,
      indexed: 0,
      processing: 0,
      error: 0
    };

    documents.forEach(doc => {
      const status = doc.processing_status || (doc.processed ? 'indexed' : 'processing');
      if (counts[status] !== undefined) {
        counts[status]++;
      }
    });

    return counts;
  };

  const statusCounts = getStatusCounts();

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Document Management</h2>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center space-x-2 rounded-md bg-secondary px-3 py-2 text-sm hover:bg-secondary/80"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="-mb-px flex space-x-8">
          {showUploadTab && (
            <button
              onClick={() => setActiveTab('upload')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'upload'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Upload className="h-4 w-4" />
                <span>Upload Documents</span>
              </div>
            </button>
          )}
          <button
            onClick={() => setActiveTab('manage')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'manage'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
            }`}
          >
            <div className="flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Manage Documents</span>
              {documents.length > 0 && (
                <span className="bg-primary/10 text-primary text-xs px-2 py-1 rounded-full">
                  {documents.length}
                </span>
              )}
            </div>
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'upload' && (
          <div className="space-y-4">
            <FileUpload onUploadComplete={handleUploadComplete} />
            <div className="text-center text-sm text-muted-foreground">
              <p>Supported formats: PDF, TXT, PPTX, IPYNB</p>
              <p>Maximum file size: 20MB</p>
            </div>
          </div>
        )}

        {activeTab === 'manage' && (
          <div className="space-y-6">
            {/* Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-card border rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5 text-blue-500" />
                  <div>
                    <p className="text-sm font-medium">Total Documents</p>
                    <p className="text-2xl font-bold">{statusCounts.all}</p>
                  </div>
                </div>
              </div>
              <div className="bg-card border rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <Package className="h-5 w-5 text-green-500" />
                  <div>
                    <p className="text-sm font-medium">Ready</p>
                    <p className="text-2xl font-bold text-green-600">{statusCounts.indexed}</p>
                  </div>
                </div>
              </div>
              <div className="bg-card border rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <RefreshCw className="h-5 w-5 text-blue-500" />
                  <div>
                    <p className="text-sm font-medium">Processing</p>
                    <p className="text-2xl font-bold text-blue-600">{statusCounts.processing}</p>
                  </div>
                </div>
              </div>
              <div className="bg-card border rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <HardDrive className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Total Size</p>
                    <p className="text-2xl font-bold">
                      {formatFileSize(documents.reduce((sum, doc) => sum + (doc.file_size || doc.size || 0), 0))}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Search, Filter, and Sort */}
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search documents by name..."
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
                  <option value="all">All Status ({statusCounts.all})</option>
                  <option value="indexed">Ready ({statusCounts.indexed})</option>
                  <option value="processing">Processing ({statusCounts.processing})</option>
                  <option value="error">Error ({statusCounts.error})</option>
                </select>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">Sort by:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-3 py-2 border border-input rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                >
                  <option value="created_at">Upload Date</option>
                  <option value="name">Name</option>
                  <option value="size">File Size</option>
                  <option value="status">Status</option>
                </select>
                <button
                  onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="px-2 py-2 border border-input rounded-md bg-background hover:bg-accent"
                  title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
                >
                  {sortOrder === 'asc' ? '↑' : '↓'}
                </button>
              </div>
            </div>

            {/* Document List */}
            <div className="min-h-[400px]">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-2" />
                    <p className="text-muted-foreground">Loading documents...</p>
                  </div>
                </div>
              ) : (
                <DocumentList
                  documents={filteredAndSortedDocuments}
                  onDocumentSelect={onDocumentSelect}
                  selectedDocuments={selectedDocuments}
                  onRefresh={handleRefresh}
                  showHeader={false}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
