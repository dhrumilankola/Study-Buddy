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
import { getChatSession, endVoiceChat } from './api';

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
  const [currentSessionData, setCurrentSessionData] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [showDocumentManager, setShowDocumentManager] = useState(false);
  const [sessionDocuments, setSessionDocuments] = useState([]);

  const handleNavigation = (view) => {
    if (view === currentView && !showUpload) return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentView(view);
      setShowUpload(false);
      setIsTransitioning(false);
    }, 150);
  };

  const handleUploadClick = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowUpload(true);
      setIsTransitioning(false);
    }, 150);
  };

  const handleUploadComplete = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowUpload(false);
      setCurrentView('documents');
      setIsTransitioning(false);
    }, 150);
  };

  const handleSessionSelect = async (sessionUuid) => {
    try {
      setCurrentSessionId(sessionUuid);
      setCurrentView('chat');
      
      if (isMobile) {
        setSidebarOpen(false);
      }

      const sessionData = await getChatSession(sessionUuid);
      setCurrentSessionData(sessionData);
    } catch (error) {
      console.error('Error fetching session data:', error);
      setCurrentSessionData(null);
    }
  };

  const handleNewSession = async (session) => {
    try {
      setCurrentSessionId(session.session_uuid);
      setCurrentView('chat');
      
      const sessionData = await getChatSession(session.session_uuid);
      setCurrentSessionData(sessionData);
    } catch (error) {
      console.error('Error fetching new session data:', error);
      setCurrentSessionData(session);
    }
  };

  const handleSwitchToVoice = () => {
    setCurrentView('chat');
    alert("Please create a new Voice Chat session to use voice features.");
  };

  const handleEndVoiceSession = async (sessionUuid) => {
    try {
      await endVoiceChat(sessionUuid);
      console.log('Voice session ended successfully');
    } catch (error) {
      console.error('Error ending voice session:', error);
    }
  };

  const handleManageDocuments = (sessionUuid) => {
    setShowDocumentManager(true);
  };

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
              <ChatInterface 
                sessionUuid={currentSessionId}
                sessionData={currentSessionData}
                onSwitchToVoice={handleSwitchToVoice}
                onEndVoiceSession={handleEndVoiceSession}
              />
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
              {currentSessionData && (
                <Typography variant="caption" sx={{ ml: 2, opacity: 0.8 }}>
                  {currentSessionData.session_type === 'voice' ? '🎙️ Voice' : '💬 Text'} Session
                </Typography>
              )}
            </Typography>
          </Toolbar>
        </AppBar>

        <Drawer
          variant={isMobile ? 'temporary' : 'persistent'}
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
          <Toolbar />
          <Box sx={{ overflow: 'auto', height: '100%' }}>
            <Layout
              currentView={currentView}
              onNavigate={handleNavigation}
              onUpload={handleUploadClick}
              showUpload={showUpload}
              isTransitioning={isTransitioning}
            />
            <ChatSessionManager
              onSessionSelect={handleSessionSelect}
              onSessionCreated={handleNewSession}
              currentSessionId={currentSessionId}
              onManageDocuments={handleManageDocuments}
            />
          </Box>
        </Drawer>

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            height: '100vh',
            ml: sidebarOpen && !isMobile ? 0 : `-${DRAWER_WIDTH}px`,
            transition: 'margin 0.3s',
          }}
        >
          <Toolbar />
          <Box
            sx={{
              flexGrow: 1,
              display: 'flex',
              flexDirection: 'column',
              opacity: isTransitioning ? 0 : 1,
              transition: 'opacity 0.15s ease-in-out',
            }}
          >
            {renderMainContent()}
          </Box>
        </Box>

        <SessionDocumentManager
          isOpen={showDocumentManager}
          onClose={() => setShowDocumentManager(false)}
          sessionUuid={currentSessionId}
        />
      </Box>
    </ThemeProvider>
  );
}