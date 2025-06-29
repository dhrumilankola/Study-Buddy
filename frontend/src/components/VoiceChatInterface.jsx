import { useEffect, useState } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Loader2, AlertCircle, Phone, PhoneOff } from 'lucide-react';
import { Conversation } from '@elevenlabs/client';
import { getVoiceChatConfig } from '../api';

export default function VoiceChatInterface({ sessionUuid, onEndSession }) {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [conversation, setConversation] = useState(null);

  useEffect(() => {
    fetchConfigAndConnect();
    
    return () => {
      if (conversation) {
        conversation.endSession();
      }
    };
  }, [sessionUuid]);

  const fetchConfigAndConnect = async () => {
    try {
      setIsConnecting(true);
      const data = await getVoiceChatConfig();
      setConfig(data);
      await initializeConversation(data);
    } catch (err) {
      setError('Failed to initialize voice chat');
      console.error('Voice chat initialization error:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  const initializeConversation = async (config) => {
    try {
      // Request microphone permission first
      await navigator.mediaDevices.getUserMedia({ audio: true });

      console.log('Starting ElevenLabs conversation with config:', { agentId: config.agent_id });
      const conv = await Conversation.startSession({
        agentId: config.agent_id,
        onConnect: () => {
          setIsConnected(true);
          setConnectionStatus('connected');
          console.log('Voice chat connected');
        },
        onDisconnect: () => {
          setIsConnected(false);
          setConnectionStatus('disconnected');
          console.log('Voice chat disconnected');
        },
        onError: (error) => {
          setError('Connection error occurred');
          console.error('Voice chat error:', error);
        },
        onModeChange: (mode) => {
          setIsSpeaking(mode.mode === 'speaking');
        }
      });

      setConversation(conv);
    } catch (err) {
      setError('Failed to start voice conversation');
      console.error('Conversation initialization error:', err);
    }
  };

  const handleToggleMute = async () => {
    if (!conversation) return;
    
    try {
      if (isMuted) {
        await conversation.setVolume({ volume: 1.0 });
      } else {
        await conversation.setVolume({ volume: 0.0 });
      }
      setIsMuted(!isMuted);
    } catch (err) {
      console.error('Error toggling mute:', err);
    }
  };

  const handleEndCall = async () => {
    try {
      if (conversation) {
        await conversation.endSession();
        setConversation(null);
      }
      setIsConnected(false);
      onEndSession?.(sessionUuid);
    } catch (err) {
      console.error('Error ending call:', err);
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-500';
      case 'connecting': return 'text-yellow-500';
      case 'disconnected': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'disconnected': return 'Disconnected';
      default: return 'Unknown';
    }
  };

  if (error) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border bg-card">
        <div className="text-center p-8">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Voice Chat Error</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button
            onClick={fetchConfigAndConnect}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (isConnecting || !config) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border bg-card">
        <div className="text-center p-8">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">Initializing Voice Mode</h3>
          <p className="text-muted-foreground">Connecting to voice assistant...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card">
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
            <h2 className="text-lg font-semibold">Voice Chat</h2>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`text-sm font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className={`relative mx-auto w-32 h-32 rounded-full mb-8 ${isSpeaking ? 'bg-gradient-to-r from-blue-500 to-purple-600 animate-pulse' : 'bg-gradient-to-r from-gray-400 to-gray-600'} transition-all duration-300`}>
            <div className="absolute inset-4 bg-white rounded-full flex items-center justify-center">
              {isSpeaking ? (
                <Volume2 className="h-12 w-12 text-blue-600" />
              ) : (
                <Mic className="h-12 w-12 text-gray-600" />
              )}
            </div>
            {isSpeaking && (
              <div className="absolute inset-0 rounded-full border-4 border-blue-300 animate-ping"></div>
            )}
          </div>

          <h3 className="text-xl font-semibold mb-2">
            {isSpeaking ? 'Speaking...' : 'Ready to Listen'}
          </h3>
          
          <p className="text-muted-foreground mb-8">
            {isConnected 
              ? 'Start speaking to interact with your study assistant'
              : 'Connecting to voice assistant...'
            }
          </p>

          <div className="flex items-center justify-center space-x-4">
            <button
              onClick={handleToggleMute}
              disabled={!isConnected}
              className={`p-4 rounded-full transition-all duration-200 ${
                isMuted 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
            </button>

            <button
              onClick={handleEndCall}
              disabled={!isConnected}
              className="p-4 rounded-full bg-red-500 hover:bg-red-600 text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              title="End Call"
            >
              <PhoneOff className="h-6 w-6" />
            </button>
          </div>
        </div>
      </div>

      <div className="border-t bg-muted/30 px-6 py-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>Powered by ElevenLabs AI</span>
          <span>Session: {sessionUuid?.slice(0, 8)}...</span>
        </div>
      </div>
    </div>
  );
}