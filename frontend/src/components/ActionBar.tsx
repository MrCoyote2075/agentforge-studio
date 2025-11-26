'use client';

import { useState } from 'react';
import { Download, Github, Loader2 } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import { downloadZip } from '@/lib/api';
import { StageIndicator } from './StageIndicator';

export function ActionBar() {
  const { project, stage, files } = useProjectContext();
  const [isDownloading, setIsDownloading] = useState(false);

  const hasFiles = files.filter((f) => f.type === 'file').length > 0;

  const handleDownload = async () => {
    if (!project) return;

    setIsDownloading(true);
    try {
      const blob = await downloadZip(project.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project.name.replace(/\s+/g, '_')}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex items-center justify-between border-t border-surface-light bg-background px-4 py-2">
      {/* Stage indicator */}
      <div className="flex-1 overflow-hidden">
        {project ? (
          <StageIndicator stage={stage} />
        ) : (
          <span className="text-sm text-gray-500">
            Create a project to get started
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center space-x-2">
        <button
          onClick={handleDownload}
          disabled={!project || !hasFiles || isDownloading}
          className="flex items-center space-x-2 rounded bg-success px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isDownloading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          <span>Download ZIP</span>
        </button>

        <button
          disabled
          className="flex items-center space-x-2 rounded bg-surface px-3 py-1.5 text-sm font-medium text-gray-400 transition-colors hover:bg-surface-light disabled:cursor-not-allowed disabled:opacity-50"
          title="Coming soon"
        >
          <Github className="h-4 w-4" />
          <span>Push to GitHub</span>
        </button>
      </div>
    </div>
  );
}
