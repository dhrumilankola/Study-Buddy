import { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Drawer, AppBar, Toolbar, Typography, IconButton } from '@mui/material';
import { Menu as MenuIcon, Mic, MessageSquare } from '@mui/icons-material';
import ChatInterface from './components/ChatInterface';
import DocumentManager from './components/DocumentManager';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';
import VoiceChatInterface from './components/VoiceChatInterface';
import ChatSessionManager from './components/ChatSessionManager';
import SessionDocumentManager from './components/SessionDocumentManager';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
  },
});

const DRAWER_WIDTH = 320;

export default function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [showUpload, setShowUpload] = useState(false);
  const [chatMode, setChatMode] = useState('text'); // 'text' or 'voice'
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [showSessionDocManager, setShowSessionDocManager] = useState(false);

  // Handle session selection from the sidebar
  const handleSessionSelect = (sessionUuid) => {
    setCurrentSessionId(sessionUuid);
    setCurrentView('chat');
    if (isMobile) setSidebarOpen(false);
  };

  // Handle creation of a new session
  const handleNewSession = (session) => {
    setCurrentSessionId(session.session_uuid);
    setCurrentView('chat');
  };
  
  // Handle document management for a session
  const handleManageSessionDocuments = (sessionUuid) => {
    setCurrentSessionId(sessionUuid);
    setShowSessionDocManager(true);
  };

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Main content renderer
  const renderMainContent = () => {
    if (showUpload) {
      return <FileUpload onComplete={() => setShowUpload(false)} onClose={() => setShowUpload(false)} />;
    }

    if (!currentSessionId) {
      return (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h5">Welcome to Study Buddy</Typography>
          <Typography>Please select a session or create a new one to begin.</Typography>
        </Box>
      );
    }
    
    switch (currentView) {
      case 'chat':
        return (
          <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <StatusIndicator sessionId={currentSessionId} />
            <ChatModeToggle />
            {chatMode === 'text' ? (
              <ChatInterface key={currentSessionId} sessionUuid={currentSessionId} />
            ) : (
              <VoiceChatInterface key={currentSessionId} sessionUuid={currentSessionId} />
            )}
          </Box>
        );
      case 'documents':
        return <DocumentManager />;
      default:
        return null;
    }
  };

  const ChatModeToggle = () => (
    <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
      <button
        onClick={() => setChatMode('text')}
        className={`flex items-center space-x-2 px-3 py-1 rounded-l-lg font-medium transition-all ${chatMode === 'text' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
      >
        <MessageSquare fontSize="small" />
        <span>Text</span>
      </button>
      <button
        onClick={() => setChatMode('voice')}
        className={`flex items-center space-x-2 px-3 py-1 rounded-r-lg font-medium transition-all ${chatMode === 'voice' ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
      >
        <Mic fontSize="small" />
        <span>Voice</span>
      </button>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        <AppBar
          position="fixed"
          sx={{
            zIndex: (theme) => theme.zIndex.drawer + 1,
            width: !sidebarOpen ? '100%' : `calc(100% - ${DRAWER_WIDTH}px)`,
            transition: 'width 0.3s'
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              edge="start"
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div">Study Buddy</Typography>
          </Toolbar>
        </AppBar>

        <Drawer
          variant={isMobile ? "temporary" : "persistent"}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          <ChatSessionManager
            onSessionSelect={handleSessionSelect}
            currentSessionId={currentSessionId}
            onNewSession={handleNewSession}
            onManageDocuments={handleManageSessionDocuments}
            onUploadClick={() => setShowUpload(true)}
          />
        </Drawer>

        <Box component="main" sx={{ flexGrow: 1, height: '100vh', overflow: 'hidden' }}>
          <Toolbar />
          <Box sx={{ height: 'calc(100vh - 64px)', overflowY: 'auto' }}>
            {renderMainContent()}
          </Box>
        </Box>
        
        <SessionDocumentManager
          sessionUuid={currentSessionId}
          isOpen={showSessionDocManager}
          onClose={() => setShowSessionDocManager(false)}
        />
      </Box>
    </ThemeProvider>
  );
}