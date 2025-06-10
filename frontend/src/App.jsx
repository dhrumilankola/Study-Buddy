import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';
import VoiceChatInterface from './components/VoiceChatInterface'; // Import VoiceChatInterface

export default function App() {
  const [currentView, setCurrentView] = useState('chat'); // Default view
  const [showUpload, setShowUpload] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Handle view transitions
  const handleNavigation = (view) => {
    if (view === currentView && !showUpload) return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentView(view);
      setShowUpload(false);
      setIsTransitioning(false);
    }, 150); // Match this with CSS transition duration
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
      setCurrentView('documents'); // Navigate to documents view after upload
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
            <ChatInterface />
          </div>
        );
      case 'documents':
        return (
          <div className="space-y-6 animate-fade-in">
            <StatusIndicator />
            <DocumentList />
          </div>
        );
      case 'voice_chat': // Add case for voice_chat
        return (
          <div className="space-y-6 animate-fade-in">
            <StatusIndicator />
            <VoiceChatInterface />
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
    >
      <div className="container mx-auto px-4">
        {/* Transition wrapper */}
        <div className={`transition-opacity duration-150 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
          {renderCurrentView()}
        </div>
      </div>
    </Layout>
  );
}