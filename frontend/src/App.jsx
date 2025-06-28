import { useState, useEffect } from 'react';
import { PanelLeftClose, PanelRightClose, MessageSquare, Mic } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import DocumentManager from './components/DocumentManager';
import FileUpload from './components/FileUpload';
import ChatSessionManager from './components/ChatSessionManager';
import SessionDocumentManager from './components/SessionDocumentManager';

// This is the new header component, integrated into the main view
const MainHeader = ({ chatMode, setChatMode, sidebarOpen, setSidebarOpen }) => {
  // We can add model selection here later
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          {sidebarOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelRightClose className="h-5 w-5" />}
        </button>
        <h1 className="text-lg font-semibold">Study Buddy</h1>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setChatMode('text')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium ${
            chatMode === 'text'
              ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
              : 'hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
        >
          <MessageSquare className="h-4 w-4" />
        </button>
        <button
          onClick={() => setChatMode('voice')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium ${
            chatMode === 'voice'
              ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
              : 'hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
        >
          <Mic className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [chatMode, setChatMode] = useState('text');
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSessionDocManager, setShowSessionDocManager] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleSessionSelect = (sessionUuid) => {
    setCurrentSessionId(sessionUuid);
    setCurrentView('chat');
  };

  const handleNewSession = (session) => {
    setCurrentSessionId(session.session_uuid);
    setCurrentView('chat');
  };

  const handleManageSessionDocuments = (sessionUuid) => {
    setCurrentSessionId(sessionUuid);
    setShowSessionDocManager(true);
  };
  
  const renderMainContent = () => {
    if (!currentSessionId && currentView === 'chat') {
      return (
        <div className="flex flex-col items-center justify-center h-full">
          <MessageSquare className="h-16 w-16 text-gray-400 mb-4" />
          <h2 className="text-2xl font-semibold text-gray-600 dark:text-gray-300">Welcome to Study Buddy</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Select a session or create a new one to begin.</p>
        </div>
      );
    }
    
    switch (currentView) {
      case 'chat':
        return <ChatInterface sessionUuid={currentSessionId} mode={chatMode} />;
      case 'documents':
        return <DocumentManager />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <aside
        className={`transition-all duration-300 ease-in-out bg-gray-50 dark:bg-gray-950/50 border-r border-gray-200 dark:border-gray-800 flex flex-col ${
          sidebarOpen ? 'w-72' : 'w-0'
        }`}
        style={{ visibility: sidebarOpen ? 'visible' : 'hidden' }}
      >
        <ChatSessionManager
          onSessionSelect={handleSessionSelect}
          currentSessionId={currentSessionId}
          onNewSession={handleNewSession}
          onManageDocuments={handleManageSessionDocuments}
        />
      </aside>

      <main className="flex-1 flex flex-col h-screen">
        <MainHeader chatMode={chatMode} setChatMode={setChatMode} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="flex-1 overflow-y-auto p-4">
          {renderMainContent()}
        </div>
      </main>
      
      <SessionDocumentManager
        sessionUuid={currentSessionId}
        isOpen={showSessionDocManager}
        onClose={() => setShowSessionDocManager(false)}
      />
    </div>
  );
}