import { useState } from 'react';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';

export default function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [showUpload, setShowUpload] = useState(false);

  // Function to handle navigation from header
  const handleNavigation = (view) => {
    setCurrentView(view);
    setShowUpload(false);
  };

  // Function to handle upload button click
  const handleUploadClick = () => {
    setShowUpload(true);
  };

  return (
    <Layout onNavigate={handleNavigation} onUploadClick={handleUploadClick}>
      <div className="container mx-auto px-4">
        {/* Status indicator at the top */}
        <div className="mb-6">
          <StatusIndicator />
        </div>

        {/* Main content area */}
        <div className="space-y-6">
          {showUpload ? (
            <FileUpload onClose={() => setShowUpload(false)} />
          ) : (
            <>
              {currentView === 'chat' && <ChatInterface />}
              {currentView === 'documents' && <DocumentList />}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}