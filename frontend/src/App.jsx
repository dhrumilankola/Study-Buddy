import { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Drawer, AppBar, Toolbar, Typography } from '@mui/material';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DocumentManager from './components/DocumentManager';
import FileUpload from './components/FileUpload';
import StatusIndicator from './components/StatusIndicator';
import SessionDocuments from './components/SessionDocuments';
import SessionDocumentManager from './components/SessionDocumentManager';
import { getChatSession, endVoiceChat } from './api';
import ThemeToggle from './components/ThemeToggle';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#00c08b', // ChatGPT teal
    },
    secondary: {
      main: '#2d8cff', // Gemini blue
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
            ml: sidebarOpen ? `${sidebarCollapsed ? 60 : DRAWER_WIDTH}px` : 0,
            width: sidebarOpen ? `calc(100% - ${sidebarCollapsed ? 60 : DRAWER_WIDTH}px)` : '100%',
            transition: 'margin 0.3s, width 0.3s',
            backgroundColor: 'hsl(var(--background))',
            color: 'hsl(var(--foreground))',
            borderBottom: '1px solid hsl(var(--border))',
          }}
        >
          <Toolbar disableGutters>
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, pl: 2 }}>
              Study Buddy
              {currentSessionData && (
                <Typography variant="caption" sx={{ ml: 2, opacity: 0.8 }}>
                  {currentSessionData.session_type === 'voice' ? '🎙️ Voice' : '💬 Text'} Session
                </Typography>
              )}
            </Typography>

            {/* Theme toggle button */}
            <ThemeToggle />
          </Toolbar>
        </AppBar>

        <Drawer
          variant={isMobile ? 'temporary' : 'persistent'}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          sx={{
            width: sidebarCollapsed ? 60 : DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: sidebarCollapsed ? 60 : DRAWER_WIDTH,
              boxSizing: 'border-box',
              backgroundColor: 'hsl(var(--background))',
              color: 'hsl(var(--foreground))',
              borderRight: '1px solid hsl(var(--border))',
              '& .MuiTypography-root': {
                color: 'inherit',
              },
              '& .MuiSvgIcon-root': {
                color: 'inherit',
              },
            },
          }}
        >
          <Sidebar
            onSessionSelect={handleSessionSelect}
            currentSessionId={currentSessionId}
            onNewSession={handleNewSession}
            onNavigateDocuments={() => handleNavigation('documents')}
            collapsed={sidebarCollapsed}
            onToggleCollapse={() => setSidebarCollapsed(prev => !prev)}
          />
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

            {/* {currentView === 'chat' && (
              <Box sx={{ position: 'fixed', bottom: 24, right: 24 }}>
                <StatusIndicator />
              </Box>
            )} */}
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