import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, User, Bot } from 'lucide-react';

const accent = 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)'; // emerald/teal
const userBubbleStyle = {
  background: accent,
  color: 'white',
  boxShadow: '0 2px 12px 0 rgba(16,185,129,0.08)',
  border: 'none',
  backdropFilter: 'blur(2px)',
};
const assistantBubbleStyle = {
  background: 'rgba(255,255,255,0.7)',
  color: '#222',
  boxShadow: '0 2px 12px 0 rgba(0,0,0,0.04)',
  border: '1px solid rgba(0,0,0,0.04)',
  backdropFilter: 'blur(2px)',
};
const errorBubbleStyle = {
  background: 'rgba(239,68,68,0.1)',
  color: '#ef4444',
  border: '1px solid #ef4444',
};

const StreamingCursor = () => (
  <span className="inline-block w-2 h-5 align-middle bg-gray-400 animate-pulse ml-1" style={{ borderRadius: 2 }} />
);

const MessageBubble = memo(({ message, isStreaming }) => {
  const isUser = message.type === 'user';
  const isError = message.isError;
  return (
    <div
      className={`flex items-start space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''} message-enter`}
      style={{ animation: 'message-slide-in 0.3s ease-out' }}
    >
      <div className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full shadow-lg`}
        style={isUser ? { background: accent } : { background: '#f3f4f6' }}
      >
        {isUser ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-gray-500" />}
      </div>
      <div
        className={`flex max-w-[80%] flex-col gap-2 rounded-2xl px-5 py-3 text-base shadow-lg`}
        style={isUser ? userBubbleStyle : isError ? errorBubbleStyle : assistantBubbleStyle}
      >
        {message.loading ? (
          <div className="flex items-center space-x-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        ) : (
          <>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
              p: ({ node, ...props }) => <span {...props} />,
            }}>
              {message.content}
            </ReactMarkdown>
            {isStreaming && <StreamingCursor />}
          </>
        )}
      </div>
    </div>
  );
});
MessageBubble.displayName = 'MessageBubble';

const MessageList = ({ messages, streamingIndex, isLoading, chatContainerRef, messagesEndRef }) => {
    return (
        <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
        style={{ background: 'rgba(255,255,255,0.4)', backdropFilter: 'blur(8px)' }}
        >
        {messages.map((message, index) => (
          <div key={message.id || index} className="message-enter">
            <MessageBubble message={message} isStreaming={streamingIndex === index && isLoading} />
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    );
};

export default MessageList; 