import { BookOpen, FileQuestion, UploadCloud, Menu } from 'lucide-react';
import { useState } from 'react';

export default function Header({ onNavigate, onUploadClick }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const NavButton = ({ icon: Icon, label, onClick, highlight }) => (
    <button
      onClick={() => {
        onClick();
        setMobileMenuOpen(false);
      }}
      className={`inline-flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors
        ${highlight 
          ? 'bg-primary text-primary-foreground hover:bg-primary/90' 
          : 'text-foreground/60 hover:text-foreground hover:bg-accent'
        }`}
    >
      <Icon className="mr-2 h-4 w-4" />
      {label}
    </button>
  );

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 hidden md:flex">
          <span className="text-xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            Study Buddy
          </span>
        </div>
        
        {/* Mobile menu button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 text-muted-foreground hover:text-foreground"
        >
          <Menu className="h-5 w-5" />
        </button>
        
        {/* Desktop navigation */}
        <div className="hidden md:flex flex-1 items-center justify-between space-x-2">
          <nav className="flex items-center space-x-2">
            <NavButton icon={FileQuestion} label="Chat" onClick={() => onNavigate('chat')} />
            <NavButton icon={BookOpen} label="Documents" onClick={() => onNavigate('documents')} />
            <NavButton icon={UploadCloud} label="Upload" onClick={onUploadClick} highlight />
          </nav>
        </div>

        {/* Mobile navigation */}
        {mobileMenuOpen && (
          <div className="absolute top-14 left-0 right-0 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-4 md:hidden">
            <nav className="flex flex-col space-y-2">
              <NavButton icon={FileQuestion} label="Chat" onClick={() => onNavigate('chat')} />
              <NavButton icon={BookOpen} label="Documents" onClick={() => onNavigate('documents')} />
              <NavButton icon={UploadCloud} label="Upload" onClick={onUploadClick} highlight />
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}