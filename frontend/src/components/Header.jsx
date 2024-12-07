import { BookOpen, FileQuestion, UploadCloud } from 'lucide-react';

export default function Header({ onNavigate, onUploadClick }) {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        <div className="mr-4 hidden md:flex">
          <span className="text-xl font-bold">RAG Assistant</span>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <nav className="flex items-center space-x-2">
            <button
              onClick={() => onNavigate('chat')}
              className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <FileQuestion className="mr-2 h-4 w-4" />
              Chat
            </button>
            <button
              onClick={() => onNavigate('documents')}
              className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <BookOpen className="mr-2 h-4 w-4" />
              Documents
            </button>
            <button
              onClick={onUploadClick}
              className="inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <UploadCloud className="mr-2 h-4 w-4" />
              Upload
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}