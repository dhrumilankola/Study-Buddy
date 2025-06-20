import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, Cpu, User, MessagesSquare } from 'lucide-react';
import { queryDocuments, switchModel, saveChatMessage, getChatMessages } from '../api';

export default function ChatInterface({ sessionUuid }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState('gemini');
  const [switchingModel, setSwitchingModel] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load existing messages when component mounts or sessionUuid changes
  useEffect(() => {
    const loadMessages = async () => {
      if (!sessionUuid) return;

      try {
        const existingMessages = await getChatMessages(sessionUuid);

        // Convert database messages to frontend format
        const formattedMessages = [];
        for (const msg of existingMessages) {
          // Add user message
          formattedMessages.push({
            type: 'user',
            content: msg.message_content
          });

          // Add assistant response if it exists
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    setIsLoading(true);

    // Add user message
    setMessages(prev => [...prev, { type: 'user', content: question }]);

    const startTime = Date.now();
    let messageSaved = false; // Track if we've already saved this message

    try {
      // Initialize assistant message
      let assistantMessage = '';
      setMessages(prev => [...prev, { type: 'assistant', content: '', loading: true }]);

      // Get streaming response
      const response = await queryDocuments(question, 3, selectedModel, sessionUuid);

      // Set up text decoder
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the stream chunk
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        // Process each line
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
                // Save the complete conversation to database
                console.log('Stream completed, saving message to database...');
                if (sessionUuid && assistantMessage.trim() && !messageSaved) {
                  const processingTime = Date.now() - startTime;
                  console.log(`Saving message: "${question}" -> "${assistantMessage.trim().substring(0, 100)}..."`);
                  try {
                    const savedMessage = await saveChatMessage(
                      sessionUuid,
                      question,
                      assistantMessage.trim(),
                      selectedModel,
                      null, // token_count - we don't track this yet
                      processingTime
                    );
                    console.log('Message saved successfully:', savedMessage);
                    messageSaved = true;
                  } catch (saveError) {
                    console.error('Error saving message to database:', saveError);
                  }
                } else {
                  console.log('Not saving message - missing sessionUuid, empty assistant message, or already saved');
                }
                break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      // Fallback: Save message even if stream didn't complete properly
      if (sessionUuid && assistantMessage.trim() && !messageSaved) {
        const processingTime = Date.now() - startTime;
        console.log('Stream ended, attempting fallback save...');
        console.log(`Fallback save data: sessionUuid=${sessionUuid}, question="${question}", assistantMessage="${assistantMessage.trim().substring(0, 100)}..."`);
        try {
          const savedMessage = await saveChatMessage(
            sessionUuid,
            question,
            assistantMessage.trim(),
            selectedModel,
            null,
            processingTime
          );
          console.log('Fallback save successful:', savedMessage);
          messageSaved = true;
        } catch (saveError) {
          console.error('Error in fallback save:', saveError);
        }
      } else {
        console.log('Skipping fallback save:', {
          hasSessionUuid: !!sessionUuid,
          hasAssistantMessage: !!assistantMessage.trim(),
          alreadySaved: messageSaved,
          sessionUuid,
          assistantMessageLength: assistantMessage.length
        });
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

  const MessageBubble = ({ message }) => {
    const isUser = message.type === 'user';
    const isError = message.type === 'error';

    return (
      <div className={`flex items-start space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        <div className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full ${
          isUser ? 'bg-primary' : 'bg-muted'
        }`}>
          {isUser ? (
            <User className="h-4 w-4 text-primary-foreground" />
          ) : (
            <Bot className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        <div
          className={`flex max-w-[80%] flex-col gap-2 rounded-lg px-4 py-2 text-sm ${
            isUser
              ? 'bg-primary text-primary-foreground'
              : isError
              ? 'bg-destructive/10 text-destructive'
              : 'bg-muted'
          }`}
        >
          {message.loading ? (
            <div className="flex items-center space-x-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>
      </div>
    );
  };

  // Show placeholder when no session is selected
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

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card">
      {/* Model Selector */}
      <div className="border-b px-4 py-2">
        <div className="flex items-center justify-end space-x-2">
          <button
            onClick={() => handleModelSwitch('ollama')}
            disabled={switchingModel}
            className={`inline-flex items-center space-x-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedModel === 'ollama'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent'
            }`}
          >
            <Cpu className="h-4 w-4" />
            <span>Ollama</span>
          </button>
          <button
            onClick={() => handleModelSwitch('gemini')}
            disabled={switchingModel}
            className={`inline-flex items-center space-x-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedModel === 'gemini'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent'
            }`}
          >
            <Bot className="h-4 w-4" />
            <span>Gemini</span>
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div key={index} className="animate-fade-in">
            <MessageBubble message={message} />
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
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
        </div>
      </form>
    </div>
  );
}