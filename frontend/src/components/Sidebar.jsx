import { Folder, PanelLeftClose, PanelRightOpen } from 'lucide-react';
import ChatSessionManager from './ChatSessionManager';

export default function Sidebar({
  onSessionSelect,
  currentSessionId,
  onNewSession,
  onNavigateDocuments,
  collapsed = false,
  onToggleCollapse,
}) {
  return (
    <div className="flex h-full flex-col">
      {/* Top brand avatar */}
      <div className="group relative flex items-center h-14 border-b px-2">
        <div className="h-8 w-8 rounded bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-primary-foreground font-bold">
          SB
        </div>

        {/* Toggle button */}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className={`${collapsed ? 'absolute left-0 right-0 flex justify-center items-center' : 'ml-auto'} rounded p-2 hover:bg-muted transition-opacity ${collapsed ? 'opacity-0 group-hover:opacity-100' : ''}`}
            title={collapsed ? 'Open sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelRightOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {/* Sessions list (hidden when collapsed) */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto">
          <ChatSessionManager
            onSessionSelect={onSessionSelect}
            onNewSession={onNewSession}
            currentSessionId={currentSessionId}
            onManageDocuments={onNavigateDocuments}
            showHeader={true}
          />
        </div>
      )}

      {/* Bottom actions */}
      <div className="border-t p-2 flex justify-center">
        <button
          className="inline-flex items-center space-x-2 rounded-md hover:bg-muted px-3 py-2 text-sm transition-colors"
          onClick={onNavigateDocuments}
          title="Documents"
        >
          <Folder className="h-5 w-5" />
          {!collapsed && <span>Documents</span>}
        </button>
      </div>
    </div>
  );
} 