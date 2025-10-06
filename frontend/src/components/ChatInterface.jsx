import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, Cpu, User, MessagesSquare, Mic, MessageSquare } from 'lucide-react';
import { queryDocuments, switchModel, saveChatMessage, getChatMessages } from '../api';
import VoiceChatInterface from './VoiceChatInterface';
import MarkdownRenderer from './MarkdownRenderer';

export default function ChatInterface({ sessionUuid, sessionData, onSwitchToVoice, onEndVoiceSession }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [switchingModel, setSwitchingModel] = useState(false);
  const [viewMode, setViewMode] = useState('text');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (sessionData?.session_type === 'voice') {
      setViewMode('voice');
    } else {
      setViewMode('text');
    }
  }, [sessionData]);

  useEffect(() => {
    const loadMessages = async () => {
      if (!sessionUuid || viewMode === 'voice') return;

      try {
        const existingMessages = await getChatMessages(sessionUuid);

        const formattedMessages = [];
        for (const msg of existingMessages) {
          formattedMessages.push({
            type: 'user',
            content: msg.message_content
          });

          if (msg.response_content) {
            formattedMessages.push({
              type: 'assistant',
              content: msg.response_content,
              model: msg.model_provider
            });
          }
        }

        setMessages(formattedMessages);
      } catch (error) {
        console.error('Error loading chat messages:', error);
      }
    };

    loadMessages();
  }, [sessionUuid, viewMode]);

  const handleModelSwitch = async (provider) => {
    if (provider === selectedModel || isLoading || switchingModel) return;
    
    try {
      setSwitchingModel(true);
      await switchModel(provider);
      setSelectedModel(provider);
    } catch (error) {
      console.error('Error switching model:', error);
    } finally {
      setSwitchingModel(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    setIsLoading(true);

    setMessages(prev => [...prev, { type: 'user', content: question }]);

    const startTime = Date.now();
    let messageSaved = false;

    try {
      let assistantMessage = '';
      setMessages(prev => [...prev, { type: 'assistant', content: '', loading: true }]);

      const response = await queryDocuments(question, 3, selectedModel, sessionUuid);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'error') {
                setMessages(prev => [
                  ...prev.slice(0, -1),
                  { type: 'error', content: data.content }
                ]);
                break;
              } else if (data.type === 'response') {
                assistantMessage += data.content;
                setMessages(prev => [
                  ...prev.slice(0, -1),
                  {
                    type: 'assistant',
                    content: assistantMessage,
                    model: data.provider
                  }
                ]);
              } else if (data.type === 'done') {
                if (sessionUuid && assistantMessage.trim() && !messageSaved) {
                  const processingTime = Date.now() - startTime;
                  try {
                    await saveChatMessage(
                      sessionUuid,
                      question,
                      assistantMessage.trim(),
                      selectedModel,
                      null,
                      processingTime
                    );
                    messageSaved = true;
                  } catch (saveError) {
                    console.error('Error saving message:', saveError);
                  }
                }
                break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      if (sessionUuid && assistantMessage.trim() && !messageSaved) {
        const processingTime = Date.now() - startTime;
        try {
          await saveChatMessage(
            sessionUuid,
            question,
            assistantMessage.trim(),
            selectedModel,
            null,
            processingTime
          );
        } catch (saveError) {
          console.error('Error in fallback save:', saveError);
        }
      }

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        { type: 'error', content: 'Failed to get response. Please try again.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceModeToggle = () => {
    if (sessionData?.session_type === 'voice') {
      setViewMode(viewMode === 'voice' ? 'text' : 'voice');
    } else {
      onSwitchToVoice?.();
    }
  };

  const MessageBubble = ({ message }) => {
    const isUser = message.type === 'user';
    const isError = message.type === 'error';

    if (isUser) {
      // User messages - right aligned with bubble
      return (
        <div className="flex items-start justify-end space-x-3 mb-6">
          <div className="max-w-[85%] rounded-2xl bg-primary px-4 py-3 text-primary-foreground">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
          <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full bg-primary">
            <User className="h-4 w-4 text-primary-foreground" />
          </div>
        </div>
      );
    }

    // Assistant messages - left aligned without bubble, Claude-style
    return (
      <div className="flex items-start space-x-3 mb-6">
        <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full bg-muted">
          <Bot className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="max-w-[85%] flex-1">
          {message.loading ? (
            <div className="flex items-center space-x-2 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Thinking...</span>
            </div>
          ) : isError ? (
            <div className="py-3">
              <p className="text-sm text-destructive">{message.content}</p>
            </div>
          ) : (
            // Assistant messages use markdown rendering without background
            <MarkdownRenderer content={message.content} />
          )}
        </div>
      </div>
    );
  };

  if (!sessionUuid) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border bg-card">
        <div className="text-center">
          <MessagesSquare className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">No Chat Session Selected</h3>
          <p className="text-muted-foreground mb-4">
            Create a new chat session or select an existing one to start chatting.
          </p>
        </div>
      </div>
    );
  }

  if (viewMode === 'voice' && sessionData?.session_type === 'voice') {
    return <VoiceChatInterface sessionUuid={sessionUuid} onEndSession={onEndVoiceSession} />;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card">
      <div className="border-b px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">
              {sessionData?.session_type === 'voice' ? 'Voice Session' : 'Text Session'}
            </span>
            {sessionData?.session_type === 'voice' && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">
                <Mic className="h-3 w-3 mr-1" />
                Voice Enabled
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleModelSwitch('ollama')}
              disabled={switchingModel || viewMode === 'voice'}
              className={`inline-flex items-center space-x-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                selectedModel === 'ollama'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent'
              } disabled:opacity-50`}
            >
              <Cpu className="h-4 w-4" />
              <span>Ollama</span>
            </button>
            
            <button
              onClick={() => handleModelSwitch('gemini')}
              disabled={switchingModel || viewMode === 'voice'}
              className={`inline-flex items-center space-x-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                selectedModel === 'gemini'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent'
              } disabled:opacity-50`}
            >
              <Bot className="h-4 w-4" />
              <span>Gemini</span>
            </button>

            {sessionData?.session_type === 'voice' && (
              <button
                onClick={handleVoiceModeToggle}
                className={`inline-flex items-center space-x-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === 'voice'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
                title={viewMode === 'voice' ? 'Switch to Text Mode' : 'Switch to Voice Mode'}
              >
                {viewMode === 'voice' ? (
                  <MessageSquare className="h-4 w-4" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      <div ref={chatContainerRef} className="flex-1 overflow-y-auto px-6 py-4">
        {messages.map((message, index) => (
          <div key={index} className="animate-fade-in">
            <MessageBubble message={message} />
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t bg-card p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask a question using ${selectedModel === 'gemini' ? 'Google Gemini' : 'Ollama'}...`}
            className="flex-1 min-w-0 rounded-md border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            disabled={isLoading || switchingModel}
          />
          <button
            type="submit"
            disabled={isLoading || switchingModel || !input.trim()}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
          
          {sessionData?.session_type !== 'voice' && (
            <button
              type="button"
              onClick={handleVoiceModeToggle}
              className="inline-flex items-center justify-center rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground hover:bg-secondary/90 transition-colors"
              title="Create Voice Session"
            >
              <Mic className="h-4 w-4" />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}