import Header from './Header';

export default function Layout({ children, onNavigate, onUploadClick }) {
  return (
    <div className="min-h-screen bg-background font-sans antialiased">
      <div className="relative flex min-h-screen flex-col">
        <Header onNavigate={onNavigate} onUploadClick={onUploadClick} />
        <main className="flex-1">
          <div className="container flex-1 items-start py-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}