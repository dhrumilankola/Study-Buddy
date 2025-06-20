import { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Drawer, AppBar, Toolbar, Typography, IconButton } from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import DocumentList from './components/DocumentList';
import DocumentManager from './components/DocumentManager';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';
import ChatSessionManager from './components/ChatSessionManager';
import SessionDocuments from './components/SessionDocuments';
import SessionDocumentManager from './components/SessionDocumentManager';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const DRAWER_WIDTH = 320;

export default function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [showUpload, setShowUpload] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [showDocumentManager, setShowDocumentManager] = useState(false);
  const [sessionDocuments, setSessionDocuments] = useState([]);

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

  // Handle session selection
  const handleSessionSelect = (sessionUuid) => {
    setCurrentSessionId(sessionUuid);
    setCurrentView('chat');
    // Close sidebar on mobile when session is selected
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  // Handle new session creation
  const handleNewSession = (session) => {
    setCurrentSessionId(session.session_uuid);
    setCurrentView('chat');
  };

  // Handle document management
  const handleManageDocuments = (sessionUuid) => {
    setShowDocumentManager(true);
  };

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setSidebarOpen(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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

  const renderMainContent = () => {
    if (showUpload) {
      return (
        <Box sx={{ p: 3 }}>
          <FileUpload onComplete={handleUploadComplete} onClose={() => setShowUpload(false)} />
        </Box>
      );
    }

    switch (currentView) {
      case 'chat':
        return (
          <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <StatusIndicator />
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <ChatInterface sessionUuid={currentSessionId} />
            </Box>
          </Box>
        );
      case 'documents':
        return (
          <Box sx={{ p: 3 }}>
            <StatusIndicator />
            <DocumentManager showUploadTab={true} />
          </Box>
        );
      case 'session-documents':
        return (
          <Box sx={{ height: '100%' }}>
            <SessionDocuments sessionUuid={currentSessionId} />
          </Box>
        );
      default:
        return null;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        {/* App Bar */}
        <AppBar
          position="fixed"
          sx={{
            zIndex: (theme) => theme.zIndex.drawer + 1,
            ml: sidebarOpen ? `${DRAWER_WIDTH}px` : 0,
            width: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%',
            transition: 'margin 0.3s, width 0.3s'
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="toggle sidebar"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              edge="start"
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              Study Buddy
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Sidebar */}
        <Drawer
          variant={isMobile ? "temporary" : "persistent"}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar /> {/* Spacer for app bar */}
          <ChatSessionManager
            onSessionSelect={handleSessionSelect}
            currentSessionId={currentSessionId}
            onNewSession={handleNewSession}
            onManageDocuments={handleManageDocuments}
          />
        </Drawer>

        {/* Main Content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            height: '100vh',
            overflow: 'hidden',
            ml: sidebarOpen && !isMobile ? 0 : 0,
            transition: 'margin 0.3s'
          }}
        >
          <Toolbar /> {/* Spacer for app bar */}
          <Box sx={{ height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
            {renderMainContent()}
          </Box>
        </Box>

        {/* Session Document Manager Modal */}
        <SessionDocumentManager
          sessionUuid={currentSessionId}
          sessionDocuments={sessionDocuments}
          onDocumentsUpdate={setSessionDocuments}
          isOpen={showDocumentManager}
          onClose={() => setShowDocumentManager(false)}
        />
      </Box>
    </ThemeProvider>
  );
}