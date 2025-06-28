import Header from './Header';
import { useState } from 'react';

export default function Layout({ children, onNavigate, onUploadClick, currentView }) {
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen font-sans antialiased" style={{ background: 'var(--gradient-glass)' }}>
      <div className="relative flex min-h-screen flex-col">
        <div className="flex items-center justify-between px-4 pt-4">
          <Header 
            onNavigate={onNavigate} 
            onUploadClick={onUploadClick} 
            currentView={currentView}
          />
          <button
            onClick={toggleDarkMode}
            className="ml-4 rounded-full p-2 bg-background/70 shadow hover:bg-background/90 border border-border transition-colors"
            aria-label="Toggle dark mode"
          >
            {darkMode ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.07l-.71.71M21 12h-1M4 12H3m16.66 5.66l-.71-.71M4.05 4.93l-.71-.71M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z" /></svg>
            )}
          </button>
        </div>
        <main className="flex-1 overflow-hidden">
          <div className="container h-[calc(100vh-4rem)] py-6">
            {children}
          </div>
        </main>
        <div className="fixed inset-x-0 bottom-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
      </div>
    </div>
  );
}