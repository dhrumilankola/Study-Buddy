import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';
import VoiceChatInterface from './components/VoiceChatInterface';
import { Mic, MessageSquare, FileText } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState('chat'); // Default view
  const [showUpload, setShowUpload] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [chatMode, setChatMode] = useState('text'); // 'text' or 'voice'

  // Handle view transitions
  const handleNavigation = (view) => {
    if (view === currentView && !showUpload) return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentView(view);
      setShowUpload(false);
      setIsTransitioning(false);
    }, 150);
  };

  // Handle upload modal
  const handleUploadClick = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowUpload(true);
      setIsTransitioning(false);
    }, 150);
  };

  // Handle upload completion
  const handleUploadComplete = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowUpload(false);
      setCurrentView('documents');
      setIsTransitioning(false);
    }, 150);
  };

  // Handle escape key to close upload
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && showUpload) {
        setShowUpload(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [showUpload]);

  // Chat Mode Toggle Component
  const ChatModeToggle = () => (
    <div className="flex items-center bg-gray-100 rounded-lg p-1 mb-6">
      <button
        onClick={() => setChatMode('text')}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
          chatMode === 'text'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <MessageSquare className="w-4 h-4" />
        <span>Text Chat</span>
      </button>
      <button
        onClick={() => setChatMode('voice')}
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
          chatMode === 'voice'
            ? 'bg-white text-blue-600 shadow-sm'
            : 'text-gray-600 hover:text-gray-800'
        }`}
      >
        <Mic className="w-4 h-4" />
        <span>Voice Chat</span>
      </button>
    </div>
  );

  const renderCurrentView = () => {
    if (showUpload) {
      return (
        <div className="animate-fade-in">
          <FileUpload onComplete={handleUploadComplete} onClose={() => setShowUpload(false)} />
        </div>
      );
    }

    switch (currentView) {
      case 'chat':
        return (
          <div className="space-y-6 animate-fade-in">
            <StatusIndicator />
            
            {/* Chat Mode Toggle */}
            <ChatModeToggle />
            
            {/* Chat Interface based on mode */}
            {chatMode === 'text' ? (
              <div>
                <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="text-lg font-semibold text-blue-800 mb-2">Text Chat Mode</h3>
                  <p className="text-blue-700">
                    Type your questions and get detailed responses with citations from your uploaded documents.
                  </p>
                </div>
                <ChatInterface />
              </div>
            ) : (
              <div>
                <div className="mb-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <h3 className="text-lg font-semibold text-purple-800 mb-2">Voice Chat Mode</h3>
                  <p className="text-purple-700">
                    Speak naturally and get AI-powered responses based on your uploaded documents. 
                    Your voice is transcribed and processed through the same RAG system.
                  </p>
                </div>
                <VoiceChatInterface />
              </div>
            )}
          </div>
        );
        
      case 'documents':
        return (
          <div className="space-y-6 animate-fade-in">
            <StatusIndicator />
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <h3 className="text-lg font-semibold text-green-800 mb-2">Document Library</h3>
              <p className="text-green-700">
                Manage your uploaded documents. These are the sources used for both text and voice chat responses.
              </p>
            </div>
            <DocumentList />
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <Layout 
      onNavigate={handleNavigation} 
      onUploadClick={handleUploadClick}
      currentView={currentView}
    >
      <div className="container mx-auto px-4">
        {/* Main Content Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {currentView === 'chat' ? 'Study Buddy Chat' : 
                 currentView === 'documents' ? 'Document Library' : 'Study Buddy'}
              </h1>
              <p className="text-gray-600">
                {currentView === 'chat' ? 
                  (chatMode === 'voice' ? 
                    'Ask questions about your documents using voice commands' :
                    'Ask questions about your documents using text'
                  ) :
                 currentView === 'documents' ? 
                  'Manage and view your uploaded study materials' : 
                  'Your AI-powered study companion'
                }
              </p>
            </div>
            
            {/* Quick Stats */}
            {currentView === 'chat' && (
              <div className="hidden md:flex space-x-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {chatMode === 'voice' ? <Mic className="w-8 h-8 mx-auto" /> : <MessageSquare className="w-8 h-8 mx-auto" />}
                  </div>
                  <div className="text-sm text-gray-600 capitalize">{chatMode} Mode</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Transition wrapper */}
        <div className={`transition-opacity duration-150 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
          {renderCurrentView()}
        </div>
      </div>
    </Layout>
  );
}