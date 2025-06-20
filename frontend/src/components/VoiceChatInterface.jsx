import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { VoiceProvider, useVoice } from '@humeai/voice-react';
import { fetchHumeToken, createVoiceRagWebSocket } from '../api';
import { 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  AlertCircle, 
  CheckCircle, 
  Loader2,
  RefreshCw,
  WifiOff,
  MessageCircle,
  BookOpen
} from 'lucide-react';

// Enhanced WebSocket ready state management
const ReadyState = {
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
};

// Connection retry configuration
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 5000,
  backoffFactor: 2,
};

const VoiceChatControls = ({ onTranscriptionReceived, onError, isAuthenticated }) => {
  const { connect, disconnect, messages, readyState, sendCustomMessage } = useVoice();
  const [chatMessages, setChatMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ragWebSocket, setRagWebSocket] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [lastError, setLastError] = useState(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [volume, setVolume] = useState(0.8);
  
  const messagesEndRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const ragWebSocketRef = useRef(null);
  const connectionHealthRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, scrollToBottom]);

  // Enhanced RAG WebSocket management with retry logic
  const createRagWebSocketConnection = useCallback(() => {
    if (ragWebSocketRef.current?.readyState === WebSocket.OPEN) {
      return ragWebSocketRef.current;
    }

    try {
      const ws = createVoiceRagWebSocket();
      
      ws.onopen = () => {
        console.log('RAG WebSocket connected successfully');
        setRagWebSocket(ws);
        ragWebSocketRef.current = ws;
        setConnectionAttempts(0);
        setLastError(null);
        
        // Send ping to verify connection
        ws.send(JSON.stringify({ type: 'ping' }));
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRagResponse(data);
        } catch (error) {
          console.error('Error parsing RAG WebSocket message:', error);
          setLastError('Invalid response format from server');
        }
      };
      
      ws.onclose = (event) => {
        console.log('RAG WebSocket disconnected:', event.code, event.reason);
        setRagWebSocket(null);
        ragWebSocketRef.current = null;
        
        // Auto-reconnect if not manually closed
        if (event.code !== 1000 && connectionAttempts < RETRY_CONFIG.maxRetries) {
          scheduleReconnect();
        }
      };
      
      ws.onerror = (error) => {
        console.error('RAG WebSocket error:', error);
        setLastError('Connection error occurred');
        
        if (onError) {
          onError('RAG WebSocket connection failed');
        }
      };
      
      return ws;
    } catch (error) {
      console.error('Failed to create RAG WebSocket:', error);
      setLastError('Failed to establish connection');
      return null;
    }
  }, [connectionAttempts, onError]);

  // Intelligent reconnection with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (isRetrying || connectionAttempts >= RETRY_CONFIG.maxRetries) {
      return;
    }

    setIsRetrying(true);
    const delay = Math.min(
      RETRY_CONFIG.baseDelay * Math.pow(RETRY_CONFIG.backoffFactor, connectionAttempts),
      RETRY_CONFIG.maxDelay
    );

    retryTimeoutRef.current = setTimeout(() => {
      setConnectionAttempts(prev => prev + 1);
      setIsRetrying(false);
      createRagWebSocketConnection();
    }, delay);
  }, [connectionAttempts, isRetrying, createRagWebSocketConnection]);

  // Initialize RAG WebSocket connection
  useEffect(() => {
    if (isAuthenticated) {
      createRagWebSocketConnection();
    }
    
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (ragWebSocketRef.current?.readyState === WebSocket.OPEN) {
        ragWebSocketRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [isAuthenticated, createRagWebSocketConnection]);

  // Enhanced RAG response handling with better error recovery
  const handleRagResponse = useCallback((data) => {
    const { type, response, message, sources, original_question, error } = data;
    
    switch (type) {
      case 'processing':
        setIsProcessing(true);
        setLastError(null);
        break;
        
      case 'rag_response':
        setIsProcessing(false);
        setChatMessages(prev => [...prev, {
          id: `rag-${Date.now()}`,
          sender: 'Assistant',
          text: response,
          sources: sources || [],
          timestamp: new Date(),
          type: 'rag_response',
          originalQuestion: original_question
        }]);
        setLastError(null);
        break;
        
      case 'error':
        setIsProcessing(false);
        const errorMessage = error || message || 'An error occurred while processing your question.';
        setChatMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          sender: 'System',
          text: errorMessage,
          timestamp: new Date(),
          type: 'error',
          isError: true
        }]);
        setLastError(errorMessage);
        break;
        
      case 'pong':
        // Health check response - connection is healthy
        console.log('RAG WebSocket health check OK');
        break;
        
      default:
        console.log('Unknown RAG message type:', type, data);
    }
  }, []);

  // Enhanced Hume EVI message processing
  useEffect(() => {
    if (messages && messages.length > 0) {
      const latestMessage = messages[messages.length - 1];
      
      // Avoid processing duplicate messages
      const existingMessage = chatMessages.find(msg => 
        msg.id === latestMessage.id || 
        (msg.text === latestMessage.message?.content && msg.type === latestMessage.type)
      );
      
      if (existingMessage) {
        return;
      }

      switch (latestMessage.type) {
        case 'user_message':
          const transcription = latestMessage.message?.content;
          if (transcription && transcription.trim()) {
            setChatMessages(prev => [...prev, {
              id: latestMessage.id || `user-${Date.now()}`,
              sender: 'You',
              text: transcription,
              timestamp: new Date(),
              type: 'transcription'
            }]);
            
            // Send to RAG system with retry logic
            if (ragWebSocket && ragWebSocket.readyState === WebSocket.OPEN) {
              try {
                ragWebSocket.send(JSON.stringify({
                  type: 'transcription',
                  text: transcription,
                  timestamp: new Date().toISOString()
                }));
              } catch (error) {
                console.error('Failed to send transcription to RAG:', error);
                setLastError('Failed to process transcription');
              }
            } else {
              // Try to reconnect and resend
              createRagWebSocketConnection();
              setLastError('Connection lost, attempting to reconnect...');
            }
            
            if (onTranscriptionReceived) {
              onTranscriptionReceived(transcription);
            }
          }
          break;
          
        case 'assistant_message':
          const assistantText = latestMessage.message?.content;
          if (assistantText) {
            setChatMessages(prev => [...prev, {
              id: latestMessage.id || `assistant-${Date.now()}`,
              sender: 'Voice Assistant',
              text: assistantText,
              timestamp: new Date(),
              type: 'assistant_message'
            }]);
          }
          break;
          
        case 'error':
          const errorText = latestMessage.message?.content || 'Voice connection error';
          setChatMessages(prev => [...prev, {
            id: latestMessage.id || `voice-error-${Date.now()}`,
            sender: 'System',
            text: `Voice Error: ${errorText}`,
            timestamp: new Date(),
            type: 'error',
            isError: true
          }]);
          setLastError(errorText);
          break;
      }
    }
  }, [messages, ragWebSocket, chatMessages, onTranscriptionReceived, createRagWebSocketConnection]);

  // Enhanced connection handling
  const handleConnect = useCallback(async () => {
    if (readyState === ReadyState.OPEN) return;
    
    try {
      setLastError(null);
      await connect();
      setChatMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        sender: 'System',
        text: '🎤 Voice chat connected! Start speaking to ask questions about your documents.',
        timestamp: new Date(),
        type: 'system'
      }]);
    } catch (error) {
      console.error('Connection error:', error);
      const errorMessage = `Failed to connect: ${error.message}`;
      setLastError(errorMessage);
      setChatMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        sender: 'System',
        text: errorMessage,
        timestamp: new Date(),
        type: 'error',
        isError: true
      }]);
      
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [connect, readyState, onError]);

  const handleDisconnect = useCallback(async () => {
    try {
      await disconnect();
      setChatMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        sender: 'System',
        text: 'Voice chat disconnected.',
        timestamp: new Date(),
        type: 'system'
      }]);
      setLastError(null);
    } catch (error) {
      console.error('Disconnection error:', error);
    }
  }, [disconnect]);

  // Manual retry function
  const handleRetry = useCallback(() => {
    setConnectionAttempts(0);
    setLastError(null);
    setIsRetrying(false);
    
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }
    
    // Retry both voice and RAG connections
    if (readyState === ReadyState.CLOSED) {
      handleConnect();
    }
    
    createRagWebSocketConnection();
  }, [readyState, handleConnect, createRagWebSocketConnection]);

  // Clear chat messages
  const handleClearChat = useCallback(() => {
    setChatMessages([]);
    setLastError(null);
  }, []);

  // Connection status computation
  const connectionStatus = useMemo(() => {
    const voiceConnected = readyState === ReadyState.OPEN;
    const ragConnected = ragWebSocket?.readyState === WebSocket.OPEN;
    
    if (voiceConnected && ragConnected) {
      return { text: 'Connected', color: 'text-green-600', icon: CheckCircle };
    } else if (readyState === ReadyState.CONNECTING || isRetrying) {
      return { text: 'Connecting...', color: 'text-yellow-600', icon: Loader2 };
    } else if (!voiceConnected && !ragConnected) {
      return { text: 'Disconnected', color: 'text-red-600', icon: WifiOff };
    } else {
      return { text: 'Partial Connection', color: 'text-yellow-600', icon: AlertCircle };
    }
  }, [readyState, ragWebSocket, isRetrying]);

  const isConnected = readyState === ReadyState.OPEN;
  const isConnecting = readyState === ReadyState.CONNECTING || isRetrying;
  const StatusIcon = connectionStatus.icon;

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Enhanced Header with controls and status */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center space-x-3">
          <button
            onClick={handleConnect}
            disabled={isConnected || isConnecting}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              isConnected || isConnecting
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
            }`}
          >
            {isConnecting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
            <span>
              {isConnecting ? 'Connecting...' : (isConnected ? 'Connected' : 'Start Voice Chat')}
            </span>
          </button>
          
          <button
            onClick={handleDisconnect}
            disabled={!isConnected || isConnecting}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              !isConnected || isConnecting
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-red-600 text-white hover:bg-red-700 shadow-md hover:shadow-lg'
            }`}
          >
            <MicOff className="w-4 h-4" />
            <span>Stop</span>
          </button>

          {/* Retry button */}
          {lastError && (
            <button
              onClick={handleRetry}
              className="flex items-center space-x-2 px-3 py-2 rounded-lg font-medium bg-orange-600 text-white hover:bg-orange-700 transition-all duration-200"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry</span>
            </button>
          )}
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Audio controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setAudioEnabled(!audioEnabled)}
              className={`p-2 rounded-lg transition-colors ${
                audioEnabled ? 'text-gray-600 hover:text-gray-800' : 'text-red-600'
              }`}
              title={audioEnabled ? 'Disable Audio' : 'Enable Audio'}
            >
              {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
          </div>

          {/* Connection status */}
          <div className={`flex items-center space-x-2 ${connectionStatus.color}`}>
            <StatusIcon className={`w-4 h-4 ${isConnecting ? 'animate-spin' : ''}`} />
            <span className="text-sm font-medium">{connectionStatus.text}</span>
          </div>

          {/* Clear chat button */}
          <button
            onClick={handleClearChat}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title="Clear Chat History"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error banner */}
      {lastError && (
        <div className="bg-red-50 border-b border-red-200 p-3">
          <div className="flex items-center space-x-2 text-red-800">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{lastError}</span>
          </div>
        </div>
      )}

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {chatMessages.length === 0 ? (
          <div className="text-center py-8">
            <MessageCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">Ready to Chat</h3>
            <p className="text-gray-500">
              Connect your voice and start asking questions about your documents
            </p>
          </div>
        ) : (
          chatMessages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'You' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg shadow-sm ${
                  message.sender === 'You'
                    ? 'bg-blue-600 text-white'
                    : message.isError
                    ? 'bg-red-100 text-red-800 border border-red-200'
                    : message.sender === 'System'
                    ? 'bg-gray-100 text-gray-800'
                    : 'bg-white text-gray-800 border border-gray-200'
                }`}
              >
                <div className="flex items-start space-x-2">
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed">{message.text}</p>
                    
                    {/* Sources display */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-gray-200">
                        <div className="flex items-center space-x-1 mb-1">
                          <BookOpen className="w-3 h-3 text-gray-500" />
                          <p className="text-xs text-gray-600 font-medium">Sources:</p>
                        </div>
                        <div className="space-y-1">
                          {message.sources.slice(0, 3).map((source, index) => (
                            <div key={index} className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded">
                              📄 {source.filename}
                            </div>
                          ))}
                          {message.sources.length > 3 && (
                            <div className="text-xs text-gray-500">
                              +{message.sources.length - 3} more sources
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <p className="text-xs text-gray-500 mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Processing indicator */}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 px-4 py-3 rounded-lg shadow-sm border border-gray-200">
              <div className="flex items-center space-x-3">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                <span className="text-sm">Searching your documents...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

// Enhanced main component with better state management
const VoiceChatInterface = () => {
  const [authData, setAuthData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  const initializeVoiceChat = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const tokenData = await fetchHumeToken();
      
      if (!tokenData.access_token) {
        throw new Error('No access token received from server');
      }
      
      setAuthData(tokenData);
      setRetryCount(0);
    } catch (err) {
      console.error('Failed to initialize voice chat:', err);
      const errorMessage = `Failed to initialize voice chat: ${err.message}`;
      setError(errorMessage);
      
      // Auto-retry up to 3 times
      if (retryCount < 3) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          initializeVoiceChat();
        }, 2000 * (retryCount + 1));
      }
    } finally {
      setIsLoading(false);
    }
  }, [retryCount]);

  useEffect(() => {
    initializeVoiceChat();
  }, [initializeVoiceChat]);

  const handleTranscriptionReceived = useCallback((transcription) => {
    console.log('Transcription received:', transcription);
  }, []);

  const handleError = useCallback((errorMessage) => {
    setError(errorMessage);
  }, []);

  const handleRetry = useCallback(() => {
    setRetryCount(0);
    initializeVoiceChat();
  }, [initializeVoiceChat]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600 mb-2">Initializing voice chat...</p>
          {retryCount > 0 && (
            <p className="text-sm text-gray-500">Retry attempt {retryCount}/3</p>
          )}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center p-6 bg-red-50 rounded-lg border border-red-200 max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-red-800 mb-2">Voice Chat Unavailable</h3>
          <p className="text-red-600 mb-4 text-sm">{error}</p>
          <div className="space-x-2">
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Authentication check
  if (!authData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center p-6 bg-yellow-50 rounded-lg border border-yellow-200">
          <AlertCircle className="w-12 h-12 text-yellow-600 mx-auto mb-4" />
          <p className="text-yellow-800">Authentication data not available</p>
          <button
            onClick={handleRetry}
            className="mt-3 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors"
          >
            Retry Authentication
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[500px] border border-gray-200 rounded-lg overflow-hidden shadow-lg">
      <VoiceProvider
        auth={{ type: 'accessToken', value: authData.access_token }}
        configId={authData.config_id}
        hostname={authData.hostname || 'api.hume.ai'}
        onOpen={() => {
          console.log('Hume EVI connection opened');
        }}
        onClose={(event) => {
          console.log('Hume EVI connection closed:', event);
        }}
        onError={(error) => {
          console.error('Hume EVI error:', error);
          handleError(`Voice connection error: ${error.message || 'Unknown error'}`);
        }}
      >
        <VoiceChatControls 
          onTranscriptionReceived={handleTranscriptionReceived}
          onError={handleError}
          isAuthenticated={!!authData}
        />
      </VoiceProvider>
    </div>
  );
};

export default VoiceChatInterface;