import Header from './Header';

export default function Layout({ children, onNavigate, onUploadClick, currentView }) {
  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <div className="relative flex min-h-screen flex-col">
        <Header 
          onNavigate={onNavigate} 
          onUploadClick={onUploadClick} 
          currentView={currentView}
        />
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