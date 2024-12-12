import { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, Database, Bot, Loader2, Cpu, Server } from 'lucide-react';
import { checkStatus } from '../api';

export default function StatusIndicator() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); 
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

  const getModelIcon = (provider) => {
    if (provider === 'gemini') {
      return <Bot className="h-4 w-4 text-primary" />;
    }
    return <Cpu className="h-4 w-4 text-primary" />;
  };

  const getModelName = (provider, name) => {
    if (provider === 'gemini') {
      return 'Google Gemini';
    }
    return 'Ollama (Local)';
  };

  if (loading) {
    return (
      <div className="animate-pulse rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-4 w-24 bg-muted rounded" />
            <div className="h-4 w-32 bg-muted rounded" />
          </div>
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <div className="flex items-center space-x-2 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm font-medium">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-4 transition-all hover:shadow-md">
      <div className="flex flex-col space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-card-foreground">System Status</h3>
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span className="text-sm text-muted-foreground">Operational</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex items-center space-x-3 rounded-md bg-accent/50 p-3">
            <Database className="h-4 w-4 text-primary" />
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Documents Indexed</p>
              <p className="font-medium">{status?.documents_indexed || 0}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-md bg-accent/50 p-3">
            {getModelIcon(status?.current_provider)}
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Active Model</p>
              <p className="font-medium">{getModelName(status?.current_provider, status?.model_name)}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 rounded-md bg-accent/50 p-3">
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Available Models</p>
              <div className="flex space-x-2">
                <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                  Ollama
                </span>
                {status?.providers_available?.gemini && (
                  <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                    Gemini
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}