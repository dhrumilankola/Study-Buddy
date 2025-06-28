import { useState, useRef, useEffect } from 'react';
import { Bot, Cpu, MessagesSquare } from 'lucide-react';
import { queryDocuments, switchModel, saveChatMessage, getChatMessages } from '../api';
import VoiceChatInterface from './VoiceChatInterface';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const accent = 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)';

export default function ChatInterface({ sessionUuid, mode = 'text' }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [switchingModel, setSwitchingModel] = useState(false);
  const [streamingIndex, setStreamingIndex] = useState(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadMessages = async () => {
      if (!sessionUuid) {
        setMessages([]);
        return;
      }
      try {
        const existingMessages = await getChatMessages(sessionUuid);
        const formattedMessages = existingMessages.flatMap((msg, index) => {
          const userMessage = { id: `user-${msg.id || index}`, type: 'user', content: msg.message_content };
          if (msg.response_content) {
            const assistantMessage = { id: `assistant-${msg.id || index}`, type: 'assistant', content: msg.response_content, model: msg.model_provider };
            return [userMessage, assistantMessage];
          }
          return [userMessage];
        });
        setMessages(formattedMessages);
      } catch (error) {
        console.error('Error loading chat messages:', error);
        setError('Failed to load chat history.');
      }
    };
    loadMessages();
  }, [sessionUuid]);

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

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !sessionUuid) return;
    const userMessageContent = input;
    const userMessage = { id: `user-${Date.now()}`, type: 'user', content: userMessageContent };
    setInput('');
    setMessages((prev) => {
      const assistantMessage = { id: `assistant-${Date.now()}`, type: 'assistant', content: '', sources: [], loading: true };
      const newMessages = [...prev, userMessage, assistantMessage];
      setStreamingIndex(newMessages.length - 1);
      return newMessages;
    });
    setIsLoading(true);
    setError(null);
    let assistantMessageContent = '';
    try {
      const response = await queryDocuments(userMessageContent, 3, selectedModel, sessionUuid);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          setMessages(prev => {
            const newMessages = [...prev];
            if (newMessages.length > 0) newMessages[newMessages.length - 1] = { ...newMessages[newMessages.length - 1], loading: false };
            return newMessages;
          });
          setStreamingIndex(null);
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith('data:')) {
            const jsonString = line.substring(5).trim();
            if (jsonString) {
              try {
                const parsed = JSON.parse(jsonString);
                if ((parsed.type === 'content' || parsed.type === 'response' || parsed.type === 'full_response') && parsed.content) {
                  assistantMessageContent += parsed.content;
                  setMessages(prev => {
                    const newMessages = [...prev];
                    if (newMessages.length > 0) newMessages[newMessages.length - 1] = { ...newMessages[newMessages.length - 1], content: assistantMessageContent, loading: false };
                    return newMessages;
                  });
                } else if (parsed.type === 'sources') {
                  setMessages(prev => {
                    const newMessages = [...prev];
                    if (newMessages.length > 0) newMessages[newMessages.length - 1] = { ...newMessages[newMessages.length - 1], sources: parsed.sources };
                    return newMessages;
                  });
                }
              } catch (e) { console.error("Failed to parse stream chunk:", jsonString, e); }
            }
          }
        }
      }
      if (sessionUuid && assistantMessageContent) await saveChatMessage(sessionUuid, userMessageContent, assistantMessageContent);
    } catch (err) {
      setError('Failed to get response. Please try again.');
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages.length > 0) newMessages[newMessages.length - 1] = { ...newMessages[newMessages.length - 1], content: "Sorry, I couldn't get a response. Please check the console and try again.", isError: true, loading: false };
        return newMessages;
      });
      setStreamingIndex(null);
    } finally {
      setIsLoading(false);
    }
  };

  if (!sessionUuid) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl shadow-xl" style={{ background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(12px)' }}>
        <div className="text-center">
          <MessagesSquare className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">No Chat Session Selected</h3>
          <p className="text-muted-foreground mb-4">Create a new chat session or select an existing one to start chatting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col rounded-2xl shadow-2xl" style={{ background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(16px)' }}>
      <div className="border-b px-4 py-2 flex items-center justify-end sticky top-0 z-10" style={{ background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(8px)' }}>
        <button
          onClick={() => handleModelSwitch('ollama')}
          disabled={switchingModel || isLoading}
          className={`inline-flex items-center space-x-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${selectedModel === 'ollama' ? 'bg-primary text-primary-foreground scale-105' : 'text-muted-foreground hover:bg-accent/40 hover:scale-105'}`}
          style={selectedModel === 'ollama' ? { background: accent, color: 'white' } : {}}
        >
          <Cpu className="h-4 w-4" />
          <span>Ollama</span>
        </button>
        <button
          onClick={() => handleModelSwitch('gemini')}
          disabled={switchingModel || isLoading}
          className={`inline-flex items-center space-x-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ml-2 ${selectedModel === 'gemini' ? 'bg-primary text-primary-foreground scale-105' : 'text-muted-foreground hover:bg-accent/40 hover:scale-105'}`}
          style={selectedModel === 'gemini' ? { background: '#f3f4f6', color: '#222' } : {}}
        >
          <Bot className="h-4 w-4" />
          <span>Gemini</span>
        </button>
      </div>

      <MessageList 
        messages={messages} 
        streamingIndex={streamingIndex} 
        isLoading={isLoading}
        chatContainerRef={chatContainerRef}
        messagesEndRef={messagesEndRef}
      />
      {error && <div className="text-red-500 text-sm p-4 text-center">{error}</div>}
      
      {mode === 'text' ? (
        <ChatInput 
          input={input}
          setInput={setInput}
          handleSend={handleSend}
          isLoading={isLoading}
        />
      ) : (
        <div className="w-full max-w-2xl mx-auto p-4">
          <VoiceChatInterface />
        </div>
      )}
    </div>
  );
}