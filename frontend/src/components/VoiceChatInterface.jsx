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
  const { connect, disconnect, messages, readyState, sendAssistantInput } = useVoice();
  const [chatMessages, setChatMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ragWebSocket, setRagWebSocket] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [lastError, setLastError] = useState(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  
  const messagesEndRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const ragWebSocketRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleRagResponse = useCallback((data) => {
    const { type, response, message, sources, original_question, error } = data;
    switch (type) {
      case 'processing': setIsProcessing(true); setLastError(null); break;
      case 'rag_response':
        setIsProcessing(false);
        setChatMessages(prev => [...prev, { id: `rag-${Date.now()}`, sender: 'Assistant', text: response, sources: sources || [], timestamp: new Date(), type: 'rag_response', originalQuestion: original_question }]);
        // Speak the RAG answer through EVI
        try { sendAssistantInput(response); } catch (e) { console.error('Failed to send assistant_input:', e); }
        setLastError(null);
        break;
      case 'error':
        setIsProcessing(false);
        const errorMessage = error || message || 'An error occurred.';
        setChatMessages(prev => [...prev, { id: `error-${Date.now()}`, sender: 'System', text: errorMessage, timestamp: new Date(), type: 'error', isError: true }]);
        setLastError(errorMessage);
        break;
      case 'pong': break;
      default: console.log('Unknown RAG message type:', type, data);
    }
  }, [connectionAttempts, onError, handleRagResponse, sendAssistantInput]);

  const createRagWebSocketConnection = useCallback(() => {
    if (ragWebSocketRef.current?.readyState === WebSocket.OPEN) return ragWebSocketRef.current;
    try {
      const ws = createVoiceRagWebSocket();
      ws.onopen = () => { ws.send(JSON.stringify({ type: 'ping' })); setRagWebSocket(ws); ragWebSocketRef.current = ws; setConnectionAttempts(0); setLastError(null); };
      ws.onmessage = (event) => { try { handleRagResponse(JSON.parse(event.data)); } catch (e) { console.error('Error parsing RAG WS message:', e); setLastError('Invalid server response.'); } };
      ws.onclose = (event) => { ragWebSocketRef.current = null; if (event.code !== 1000 && connectionAttempts < RETRY_CONFIG.maxRetries) scheduleReconnect(); };
      ws.onerror = () => { setLastError('Connection error.'); if (onError) onError('RAG WebSocket connection failed.'); };
      return ws;
    } catch (error) { setLastError('Failed to connect.'); return null; }
  }, [connectionAttempts, onError, handleRagResponse]);

  const scheduleReconnect = useCallback(() => {
    if (isRetrying || connectionAttempts >= RETRY_CONFIG.maxRetries) return;
    setIsRetrying(true);
    const delay = Math.min(RETRY_CONFIG.baseDelay * Math.pow(RETRY_CONFIG.backoffFactor, connectionAttempts), RETRY_CONFIG.maxDelay);
    retryTimeoutRef.current = setTimeout(() => { setConnectionAttempts(prev => prev + 1); setIsRetrying(false); createRagWebSocketConnection(); }, delay);
  }, [connectionAttempts, isRetrying, createRagWebSocketConnection]);

  useEffect(() => {
    if (isAuthenticated) createRagWebSocketConnection();
    return () => {
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      if (ragWebSocketRef.current?.readyState === WebSocket.OPEN) ragWebSocketRef.current.close(1000, 'Component unmounting');
    };
  }, [isAuthenticated, createRagWebSocketConnection]);

  useEffect(() => {
    if (!messages || messages.length === 0) return;
    const latestMessage = messages[messages.length - 1];
    if (chatMessages.some(msg => msg.id === latestMessage.id)) return;

    switch (latestMessage.type) {
      case 'user_message':
        if (latestMessage.interim) break; // Skip interim transcripts
        const transcription = latestMessage.message?.content;
        if (transcription?.trim()) {
          setChatMessages(prev => [...prev, { id: latestMessage.id || `user-${Date.now()}`, sender: 'You', text: transcription, timestamp: new Date(), type: 'transcription' }]);
          if (ragWebSocket?.readyState === WebSocket.OPEN) {
            ragWebSocket.send(JSON.stringify({ type: 'transcription', text: transcription, timestamp: new Date().toISOString() }));
          } else {
            createRagWebSocketConnection();
            setLastError('Connection lost. Reconnecting...');
          }
          if (onTranscriptionReceived) onTranscriptionReceived(transcription);
        }
        break;
      case 'assistant_message':
        const assistantText = latestMessage.message?.content;
        if (assistantText) setChatMessages(prev => [...prev, { id: latestMessage.id || `assistant-${Date.now()}`, sender: 'Voice Assistant', text: assistantText, timestamp: new Date(), type: 'assistant_message' }]);
        break;
      case 'error':
        const errorText = latestMessage.message?.content || 'Voice connection error';
        setChatMessages(prev => [...prev, { id: latestMessage.id || `voice-error-${Date.now()}`, sender: 'System', text: `Voice Error: ${errorText}`, timestamp: new Date(), type: 'error', isError: true }]);
        setLastError(errorText);
        break;
    }
  }, [messages, ragWebSocket, chatMessages, onTranscriptionReceived, createRagWebSocketConnection]);

  const handleConnect = useCallback(async () => {
    if (readyState === ReadyState.OPEN) return;
    try {
      setLastError(null);
      await connect();
      setChatMessages(prev => [...prev, { id: `system-${Date.now()}`, sender: 'System', text: '🎤 Voice chat connected!', timestamp: new Date(), type: 'system' }]);
    } catch (error) {
      const errorMessage = `Failed to connect: ${error.message}`;
      setLastError(errorMessage);
      setChatMessages(prev => [...prev, { id: `error-${Date.now()}`, sender: 'System', text: errorMessage, timestamp: new Date(), type: 'error', isError: true }]);
      if (onError) onError(errorMessage);
    }
  }, [connect, readyState, onError]);

  const handleDisconnect = useCallback(async () => {
    try { await disconnect(); setChatMessages(prev => [...prev, { id: `system-${Date.now()}`, sender: 'System', text: 'Voice chat disconnected.', timestamp: new Date(), type: 'system' }]); setLastError(null); }
    catch (error) { console.error('Disconnection error:', error); }
  }, [disconnect]);

  const handleRetry = useCallback(() => {
    setConnectionAttempts(0);
    setLastError(null);
    setIsRetrying(false);
    if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
    if (readyState !== ReadyState.OPEN) handleConnect();
    createRagWebSocketConnection();
  }, [readyState, handleConnect, createRagWebSocketConnection]);

  const connectionStatus = useMemo(() => {
    const voiceConnected = readyState === ReadyState.OPEN;
    const ragConnected = ragWebSocket?.readyState === WebSocket.OPEN;
    if (voiceConnected && ragConnected) return { text: 'Connected', color: 'text-green-500', Icon: CheckCircle };
    if (readyState === ReadyState.CONNECTING || isRetrying) return { text: 'Connecting...', color: 'text-yellow-500', Icon: Loader2, animate: true };
    return { text: 'Disconnected', color: 'text-red-500', Icon: WifiOff };
  }, [readyState, ragWebSocket, isRetrying]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center space-x-2">
          {readyState !== ReadyState.OPEN ? (
            <button onClick={handleConnect} className="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2">
              <Mic className="w-4 h-4" />
              <span>Start Call</span>
            </button>
          ) : (
            <button onClick={handleDisconnect} className="px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2">
              <MicOff className="w-4 h-4" />
              <span>End Call</span>
            </button>
          )}
          {lastError && (
            <button onClick={handleRetry} className="p-2 text-sm font-semibold text-gray-700 dark:text-gray-200 bg-yellow-400 rounded-lg hover:bg-yellow-500 transition-colors flex items-center space-x-2">
              <RefreshCw className="w-4 h-4" />
              <span>Retry</span>
            </button>
          )}
        </div>
        <div className="flex items-center space-x-4">
          <button onClick={() => setAudioEnabled(!audioEnabled)} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800">
            {audioEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5 text-red-500" />}
          </button>
          <div className={`flex items-center space-x-2 text-sm font-medium ${connectionStatus.color}`}>
            <connectionStatus.Icon className={`w-4 h-4 ${connectionStatus.animate ? 'animate-spin' : ''}`} />
            <span>{connectionStatus.text}</span>
          </div>
        </div>
      </div>
      
      {lastError && (
        <div className="p-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <div className="flex items-center space-x-2 text-sm text-red-800 dark:text-red-300">
            <AlertCircle className="w-4 h-4" />
            <span>{lastError}</span>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {chatMessages.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <MessageCircle className="w-12 h-12 mx-auto mb-4" />
            <h3 className="text-lg font-medium">Ready to Chat</h3>
            <p>Connect your voice to start asking questions.</p>
          </div>
        ) : chatMessages.map((message) => (
          <div key={message.id} className={`flex items-end space-x-2 ${message.sender === 'You' ? 'justify-end' : 'justify-start'}`}>
            <div className={`px-4 py-2 rounded-lg max-w-xs lg:max-w-md ${
              message.sender === 'You' ? 'bg-blue-600 text-white' : 
              message.isError ? 'bg-red-100 text-red-800' : 
              'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
            }`}>
              <p className="text-sm">{message.text}</p>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="text-xs font-semibold mb-1 flex items-center"><BookOpen className="w-3 h-3 mr-1"/> Sources:</h4>
                  <div className="space-y-1">
                    {message.sources.slice(0, 3).map((source, index) => (
                      <div key={index} className="text-xs truncate" title={source.filename}>📄 {source.filename}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-lg"><Loader2 className="w-4 h-4 animate-spin" /></div>
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
      if (!tokenData.access_token) throw new Error('No access token received');
      setAuthData(tokenData);
      setRetryCount(0);
    } catch (err) {
      const errorMessage = `Failed to initialize voice chat: ${err.message}`;
      setError(errorMessage);
      if (retryCount < 3) setTimeout(() => { setRetryCount(prev => prev + 1); initializeVoiceChat(); }, 2000 * (retryCount + 1));
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

  const handleError = useCallback((e) => {
    setError(`An error occurred: ${e.message || 'Unknown error'}`);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full p-6 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-700">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-700 dark:text-red-300 font-semibold">Authentication Error</p>
        <p className="text-red-600 dark:text-red-400 text-sm mb-4">{error}</p>
        <button onClick={() => { setRetryCount(0); initializeVoiceChat(); }} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
          Retry
        </button>
      </div>
    );
  }
  
  if (!authData) return null;

  return (
    <div className="h-full">
      <VoiceProvider
        auth={{ type: 'accessToken', value: authData.access_token }}
        configId={authData.config_id}
        hostname={authData.hostname || 'api.hume.ai'}
        onOpen={() => console.log('Hume EVI connection opened')}
        onClose={(e) => console.log('Hume EVI connection closed:', e)}
        onError={(e) => handleError(`Voice connection error: ${e.message || 'Unknown error'}`)}
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