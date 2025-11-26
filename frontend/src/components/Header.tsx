'use client';

import { Settings, Wifi, WifiOff } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';

export function Header() {
  const { project, isConnected } = useProjectContext();

  return (
    <header className="flex h-14 items-center justify-between border-b border-surface-light bg-background px-4">
      <div className="flex items-center space-x-4">
        <h1 className="text-xl font-bold text-white">
          <span className="text-primary">AgentForge</span> Studio
        </h1>
        {project && (
          <span className="rounded bg-surface px-2 py-1 text-sm text-gray-300">
            {project.name}
          </span>
        )}
      </div>

      <div className="flex items-center space-x-4">
        {/* Connection status */}
        <div className="flex items-center space-x-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-success" />
              <span className="text-xs text-success">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-gray-400" />
              <span className="text-xs text-gray-400">Disconnected</span>
            </>
          )}
        </div>

        {/* Settings button */}
        <button
          className="rounded p-2 text-gray-400 transition-colors hover:bg-surface hover:text-white"
          aria-label="Settings"
        >
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}
