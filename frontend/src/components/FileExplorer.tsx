'use client';

import { useState } from 'react';
import {
  FolderOpen,
  FileText,
  FileCode,
  FileJson,
  File,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import type { FileInfo } from '@/types';

interface FileExplorerProps {
  onFileSelect?: (file: FileInfo) => void;
}

const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();

  switch (ext) {
    case 'html':
    case 'htm':
      return <FileCode className="h-4 w-4 text-orange-400" />;
    case 'css':
      return <FileCode className="h-4 w-4 text-blue-400" />;
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
      return <FileCode className="h-4 w-4 text-yellow-400" />;
    case 'json':
      return <FileJson className="h-4 w-4 text-green-400" />;
    case 'md':
    case 'txt':
      return <FileText className="h-4 w-4 text-gray-400" />;
    default:
      return <File className="h-4 w-4 text-gray-400" />;
  }
};

export function FileExplorer({ onFileSelect }: FileExplorerProps) {
  const { files, project } = useProjectContext();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const handleFileClick = (file: FileInfo) => {
    if (file.type === 'file') {
      setSelectedFile(file.path);
      onFileSelect?.(file);
    }
  };

  const fileCount = files.filter((f) => f.type === 'file').length;

  return (
    <div className="flex flex-col border-t border-surface-light bg-background">
      {/* Header */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between px-4 py-2 text-left transition-colors hover:bg-surface"
      >
        <div className="flex items-center space-x-2">
          <FolderOpen className="h-4 w-4 text-primary" />
          <span className="font-medium text-white">Files</span>
          <span className="rounded-full bg-surface px-2 py-0.5 text-xs text-gray-400">
            {fileCount}
          </span>
        </div>
        {isCollapsed ? (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* File list */}
      {!isCollapsed && (
        <div className="max-h-40 overflow-y-auto border-t border-surface-light">
          {!project ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              No project selected
            </div>
          ) : files.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              No files generated yet
            </div>
          ) : (
            <ul className="py-1">
              {files
                .filter((f) => f.type === 'file')
                .map((file) => (
                  <li key={file.path}>
                    <button
                      onClick={() => handleFileClick(file)}
                      className={`flex w-full items-center space-x-2 px-4 py-1.5 text-left transition-colors hover:bg-surface ${
                        selectedFile === file.path
                          ? 'bg-surface text-white'
                          : 'text-gray-300'
                      }`}
                    >
                      {getFileIcon(file.name)}
                      <span className="truncate text-sm">{file.path}</span>
                    </button>
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
