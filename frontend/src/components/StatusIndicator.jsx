import { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, Database, Bot } from 'lucide-react';
import { checkStatus } from '../api';

export default function StatusIndicator() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const data = await checkStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch system status');
      console.error('Error fetching status:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse p-4 bg-card rounded-lg">
        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-muted rounded w-1/2"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
        <div className="flex items-center space-x-2">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-card rounded-lg space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">System Status</h3>
        <div className="flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <span className="text-sm text-muted-foreground">Operational</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center space-x-2">
          <Database className="h-4 w-4 text-primary" />
          <div className="text-sm">
            <p className="text-muted-foreground">Documents</p>
            <p className="font-medium">{status?.documents_in_vector_store || 0}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Bot className="h-4 w-4 text-primary" />
          <div className="text-sm">
            <p className="text-muted-foreground">Model</p>
            <p className="font-medium">{status?.ollama_model || 'Unknown'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}