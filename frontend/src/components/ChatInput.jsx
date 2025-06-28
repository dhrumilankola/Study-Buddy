import { Send, Loader2 } from 'lucide-react';

const ChatInput = ({ input, setInput, handleSend, isLoading }) => {
  return (
    <div
      className="border-t p-4 sticky bottom-0 z-10 flex items-center justify-center"
      style={{
        background: 'rgba(255,255,255,0.7)',
        boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.10)',
        backdropFilter: 'blur(12px)',
      }}
    >
      <form onSubmit={handleSend} className="w-full max-w-2xl">
        <div className="relative flex items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            placeholder="Ask a question..."
            className="w-full resize-none rounded-2xl border border-input bg-background/80 p-3 pr-14 text-base shadow-md focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
            rows={1}
            disabled={isLoading}
            style={{ minHeight: 48, maxHeight: 120 }}
          />
          <button
            type="submit"
            className="absolute bottom-2 right-2 flex h-10 w-10 items-center justify-center rounded-full shadow-lg transition-all bg-primary text-primary-foreground hover:scale-110 hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isLoading || !input.trim()}
            style={{ background: 'linear-gradient(90deg, #10b981 0%, #06b6d4 100%)' }}
          >
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInput; 