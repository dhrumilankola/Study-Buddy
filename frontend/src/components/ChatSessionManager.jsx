import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, File, Clock, AlertCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import EnhancedSessionCreator from './EnhancedSessionCreator';
import StatusIndicator from './StatusIndicator';

const ChatSessionManager = ({
  onSessionSelect,
  currentSessionId,
  onNewSession,
  onManageDocuments,
  apiBaseUrl = 'http://localhost:8000/api/v1'
}) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newSessionDialog, setNewSessionDialog] = useState(false);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/chat/sessions`);
      if (!response.ok) throw new Error('Failed to fetch sessions');
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSessionCreated = async (session) => {
    await fetchSessions();
    onSessionSelect(session.session_uuid);
    if (onNewSession) onNewSession(session);
    onManageDocuments(session.session_uuid);
    setNewSessionDialog(false);
  };

  const deleteSession = async (sessionUuid) => {
    if (!window.confirm('Are you sure you want to delete this chat session?')) {
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionUuid}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete session');
      await fetchSessions();
      if (currentSessionId === sessionUuid) {
        onSessionSelect(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-xl font-semibold">Chat History</h2>
        <button
          onClick={() => setNewSessionDialog(true)}
          className="mt-4 w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-800 hover:bg-gray-900 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
        >
          <Plus className="-ml-1 mr-2 h-5 w-5" />
          New Chat
        </button>
      </div>

      {error && (
        <div className="p-4">
          <div className="flex items-center bg-red-100 dark:bg-red-900/30 border border-red-400 text-red-700 dark:text-red-300 px-4 py-3 rounded-md relative" role="alert">
            <AlertCircle className="h-5 w-5 mr-2" />
            <span className="block sm:inline">{error}</span>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {loading && sessions.length === 0 ? (
          <p className="text-center text-gray-500 dark:text-gray-400">Loading sessions...</p>
        ) : sessions.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 p-4">
            <MessageSquare className="mx-auto h-12 w-12" />
            <h3 className="mt-2 text-sm font-medium">No chat sessions</h3>
            <p className="mt-1 text-sm">Create a new chat to get started.</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onSessionSelect(session.session_uuid)}
              className={`w-full text-left p-3 rounded-lg transition-colors group cursor-pointer ${
                currentSessionId === session.session_uuid
                  ? 'bg-gray-200 dark:bg-gray-700'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1 overflow-hidden">
                  <p className="text-sm font-medium truncate">{session.title || `Chat ${session.id}`}</p>
                  <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 mt-1">
                    <Clock className="h-3 w-3 mr-1" />
                    <span>{formatDistanceToNow(new Date(session.last_activity), { addSuffix: true })}</span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.session_uuid);
                  }}
                  className="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <EnhancedSessionCreator
        open={newSessionDialog}
        onClose={() => setNewSessionDialog(false)}
        onSessionCreated={handleSessionCreated}
      />
      
      <div className="p-2 border-t border-gray-200 dark:border-gray-800">
        <StatusIndicator />
      </div>
    </div>
  );
};

export default ChatSessionManager;
