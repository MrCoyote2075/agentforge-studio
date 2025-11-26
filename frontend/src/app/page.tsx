'use client';

import { useState } from 'react';
import { Header } from '@/components/Header';
import { ChatPanel } from '@/components/ChatPanel';
import { PreviewPanel } from '@/components/PreviewPanel';
import { FileExplorer } from '@/components/FileExplorer';
import { FileViewer } from '@/components/FileViewer';
import { AgentActivity } from '@/components/AgentActivity';
import { ActionBar } from '@/components/ActionBar';
import { useProjectContext } from '@/context/ProjectContext';
import { Plus, FolderOpen, Loader2 } from 'lucide-react';
import type { FileInfo } from '@/types';

function CreateProjectModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string, requirements: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [requirements, setRequirements] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !requirements.trim()) {
      setError('Please fill in all fields');
      return;
    }

    setIsCreating(true);
    setError('');
    try {
      await onCreate(name.trim(), requirements.trim());
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-md rounded-lg bg-background p-6 shadow-xl">
        <h2 className="mb-4 text-xl font-bold text-white">Create New Project</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="mb-1 block text-sm text-gray-300">
              Project Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Portfolio Website"
              className="w-full rounded border border-surface-light bg-surface px-3 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none"
            />
          </div>
          <div className="mb-4">
            <label className="mb-1 block text-sm text-gray-300">
              Project Requirements
            </label>
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="I want a portfolio website with a hero section, about me page, project gallery, and contact form..."
              rows={4}
              className="w-full rounded border border-surface-light bg-surface px-3 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none"
            />
          </div>
          {error && (
            <p className="mb-4 text-sm text-error">{error}</p>
          )}
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="flex items-center space-x-2 rounded bg-primary px-4 py-2 text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{isCreating ? 'Creating...' : 'Create Project'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function WelcomeScreen({ onCreateProject }: { onCreateProject: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <FolderOpen className="mb-6 h-20 w-20 text-gray-500" />
      <h2 className="mb-2 text-2xl font-bold text-white">
        Welcome to AgentForge Studio
      </h2>
      <p className="mb-6 max-w-md text-gray-400">
        Build websites with AI agents. Create a new project to get started and
        let our team of specialized agents help you build your vision.
      </p>
      <button
        onClick={onCreateProject}
        className="flex items-center space-x-2 rounded-lg bg-primary px-6 py-3 text-lg font-medium text-white transition-colors hover:bg-blue-600"
      >
        <Plus className="h-5 w-5" />
        <span>Create New Project</span>
      </button>
    </div>
  );
}

export default function Home() {
  const { project, createProject } = useProjectContext();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);

  const handleCreateProject = async (name: string, requirements: string) => {
    await createProject(name, requirements);
  };

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <Header />

      {/* Main content */}
      <main className="flex flex-1 overflow-hidden">
        {project ? (
          <>
            {/* Left panel - Chat */}
            <div className="flex w-1/2 flex-col lg:w-2/5">
              <div className="flex-1 overflow-hidden">
                <ChatPanel />
              </div>
              <AgentActivity />
              <FileExplorer onFileSelect={setSelectedFile} />
            </div>

            {/* Right panel - Preview */}
            <div className="flex w-1/2 flex-col lg:w-3/5">
              <PreviewPanel />
            </div>
          </>
        ) : (
          <WelcomeScreen onCreateProject={() => setShowCreateModal(true)} />
        )}
      </main>

      {/* Action bar */}
      <ActionBar />

      {/* Modals */}
      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateProject}
        />
      )}

      {selectedFile && (
        <FileViewer file={selectedFile} onClose={() => setSelectedFile(null)} />
      )}
    </div>
  );
}
