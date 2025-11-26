'use client';

import { useState, useEffect } from 'react';
import { X, Copy, Check, FileCode } from 'lucide-react';
import { getFileContent } from '@/lib/api';
import { useProjectContext } from '@/context/ProjectContext';
import type { FileInfo } from '@/types';

interface FileViewerProps {
  file: FileInfo | null;
  onClose: () => void;
}

export function FileViewer({ file, onClose }: FileViewerProps) {
  const { project } = useProjectContext();
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (file && project) {
      setIsLoading(true);
      setError(null);
      getFileContent(project.id, file.path)
        .then((data) => {
          setContent(data.content);
        })
        .catch((err) => {
          setError(err.message);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [file, project]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!file) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 flex max-h-[80vh] w-full max-w-3xl flex-col rounded-lg bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-light px-4 py-3">
          <div className="flex items-center space-x-2">
            <FileCode className="h-5 w-5 text-primary" />
            <span className="font-medium text-white">{file.path}</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="flex items-center space-x-1 rounded px-2 py-1 text-gray-400 transition-colors hover:bg-surface hover:text-white"
              disabled={!content}
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-success" />
                  <span className="text-xs text-success">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  <span className="text-xs">Copy</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-400 transition-colors hover:bg-surface hover:text-white"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : error ? (
            <div className="rounded bg-error/10 p-4 text-error">
              Error loading file: {error}
            </div>
          ) : (
            <pre className="overflow-x-auto rounded bg-surface p-4 text-sm text-gray-200">
              <code>{content || 'Empty file'}</code>
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
