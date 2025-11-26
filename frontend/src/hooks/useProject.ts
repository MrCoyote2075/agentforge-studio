'use client';

import { useState, useCallback } from 'react';
import type { Project, FileInfo, ProjectStage } from '@/types';
import * as api from '@/lib/api';

interface UseProjectReturn {
  project: Project | null;
  files: FileInfo[];
  stage: ProjectStage;
  isLoading: boolean;
  error: string | null;
  loadProject: (projectId: string) => Promise<void>;
  loadFiles: (projectId: string) => Promise<void>;
  createProject: (name: string, requirements: string) => Promise<Project>;
  setStage: (stage: ProjectStage) => void;
  setProject: (project: Project | null) => void;
  setFiles: (files: FileInfo[]) => void;
}

export function useProject(): UseProjectReturn {
  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [stage, setStage] = useState<ProjectStage>('initialized');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async (projectId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getProject(projectId);
      setProject(data);
      setStage(data.stage);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadFiles = useCallback(async (projectId: string) => {
    try {
      const data = await api.getFiles(projectId);
      setFiles(data);
    } catch (err) {
      console.error('Failed to load files:', err);
    }
  }, []);

  const createProject = useCallback(
    async (name: string, requirements: string): Promise<Project> => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.createProject(name, requirements);
        setProject(data);
        setStage(data.stage);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create project';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return {
    project,
    files,
    stage,
    isLoading,
    error,
    loadProject,
    loadFiles,
    createProject,
    setStage,
    setProject,
    setFiles,
  };
}
