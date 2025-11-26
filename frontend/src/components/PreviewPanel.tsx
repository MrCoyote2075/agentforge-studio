'use client';

import { useState } from 'react';
import { RefreshCw, Maximize2, Minimize2, Monitor } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';

export function PreviewPanel() {
  const { project, files } = useProjectContext();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [previewKey, setPreviewKey] = useState(0);

  const hasHtmlFile = files.some(
    (f) => f.type === 'file' && f.path.endsWith('.html')
  );

  const handleRefresh = () => {
    setIsLoading(true);
    setPreviewKey((prev) => prev + 1);
    // Simulate loading time
    setTimeout(() => setIsLoading(false), 500);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // Preview URL would be the preview server
  const previewUrl = project
    ? `http://localhost:8080/${project.id}/index.html`
    : '';

  return (
    <div
      className={`flex flex-col bg-background ${
        isFullscreen ? 'fixed inset-0 z-50' : 'h-full'
      }`}
    >
      {/* Preview header */}
      <div className="flex items-center justify-between border-b border-surface-light px-4 py-3">
        <div className="flex items-center space-x-2">
          <Monitor className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-white">Live Preview</h2>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            disabled={!hasHtmlFile}
            className="rounded p-2 text-gray-400 transition-colors hover:bg-surface hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Refresh preview"
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
            />
          </button>
          <button
            onClick={toggleFullscreen}
            className="rounded p-2 text-gray-400 transition-colors hover:bg-surface hover:text-white"
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Preview content */}
      <div className="relative flex-1 overflow-hidden">
        {!project ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Monitor className="mb-4 h-16 w-16 text-gray-500" />
            <p className="text-gray-400">No project selected</p>
            <p className="mt-2 text-sm text-gray-500">
              Create a project to see the live preview
            </p>
          </div>
        ) : !hasHtmlFile ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <Monitor className="mb-4 h-16 w-16 text-gray-500" />
            <p className="text-gray-400">No preview available</p>
            <p className="mt-2 text-sm text-gray-500">
              The preview will appear once files are generated
            </p>
          </div>
        ) : (
          <>
            {isLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
                <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              </div>
            )}
            <iframe
              key={previewKey}
              src={previewUrl}
              title="Website Preview"
              className="h-full w-full border-0 bg-white"
              onLoad={() => setIsLoading(false)}
            />
          </>
        )}
      </div>
    </div>
  );
}
