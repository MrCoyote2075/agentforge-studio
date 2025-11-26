'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import type {
  Project,
  ChatMessage,
  FileInfo,
  ProjectStage,
  AgentStatus,
  WebSocketMessage,
} from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProject } from '@/hooks/useProject';
import { useChat } from '@/hooks/useChat';
import { getWebSocketUrl } from '@/lib/api';

interface ProjectContextType {
  // Project state
  project: Project | null;
  files: FileInfo[];
  stage: ProjectStage;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Chat state
  messages: ChatMessage[];
  isSending: boolean;

  // Agent status
  agentStatuses: AgentStatus[];
  isTyping: boolean;

  // Actions
  sendMessage: (message: string) => Promise<void>;
  loadProject: (projectId: string) => Promise<void>;
  createProject: (name: string, requirements: string) => Promise<Project>;
  refreshFiles: () => Promise<void>;
  setProject: (project: Project | null) => void;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

interface ProjectProviderProps {
  children: ReactNode;
}

export function ProjectProvider({ children }: ProjectProviderProps) {
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const {
    project,
    files,
    stage,
    isLoading,
    error,
    loadProject: loadProjectData,
    loadFiles,
    createProject: createProjectApi,
    setProject,
    setStage,
  } = useProject();

  const {
    messages,
    isLoading: isSending,
    sendMessage: sendChatMessage,
    addMessage,
    setMessages,
  } = useChat();

  const handleWebSocketMessage = useCallback(
    (message: WebSocketMessage) => {
      const { type, payload } = message;

      switch (type) {
        case 'chat_response':
          setIsTyping(false);
          if (payload && typeof payload === 'object' && 'content' in payload) {
            const chatPayload = payload as {
              content: string;
              agent_name?: string;
              timestamp?: string;
            };
            addMessage({
              id: Date.now().toString(),
              role: 'agent',
              content: chatPayload.content,
              agent_name: chatPayload.agent_name || 'Agent',
              timestamp: chatPayload.timestamp || new Date().toISOString(),
            });
          }
          break;

        case 'typing':
          setIsTyping(true);
          break;

        case 'agent_status':
          if (payload && typeof payload === 'object' && 'statuses' in payload) {
            setAgentStatuses(payload.statuses as AgentStatus[]);
          }
          break;

        case 'stage_update':
          if (payload && typeof payload === 'object' && 'stage' in payload) {
            setStage(payload.stage as ProjectStage);
          }
          break;

        case 'file_update':
          if (project) {
            loadFiles(project.id);
          }
          break;

        default:
          console.log('Unknown WebSocket message type:', type);
      }
    },
    [addMessage, loadFiles, project, setStage]
  );

  const wsUrl = useMemo(
    () => (typeof window !== 'undefined' && project ? getWebSocketUrl(project.id) : ''),
    [project]
  );

  const { isConnected, send } = useWebSocket({
    url: wsUrl,
    onMessage: handleWebSocketMessage,
    autoReconnect: true,
  });

  const loadProject = useCallback(
    async (projectId: string) => {
      await loadProjectData(projectId);
      await loadFiles(projectId);
    },
    [loadProjectData, loadFiles]
  );

  const createProject = useCallback(
    async (name: string, requirements: string): Promise<Project> => {
      const newProject = await createProjectApi(name, requirements);
      setMessages([]);
      return newProject;
    },
    [createProjectApi, setMessages]
  );

  const sendMessage = useCallback(
    async (message: string) => {
      if (!project) {
        console.warn('No project selected');
        return;
      }

      // Add user message immediately
      addMessage({
        id: Date.now().toString(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      });

      setIsTyping(true);

      // Send via WebSocket if connected, otherwise use REST API
      if (isConnected) {
        send({
          type: 'chat',
          payload: {
            content: message,
            project_id: project.id,
          },
        });
      } else {
        await sendChatMessage(message, project.id);
        setIsTyping(false);
      }
    },
    [project, isConnected, send, addMessage, sendChatMessage]
  );

  const refreshFiles = useCallback(async () => {
    if (project) {
      await loadFiles(project.id);
    }
  }, [project, loadFiles]);

  // Load files when project changes
  useEffect(() => {
    if (project) {
      loadFiles(project.id);
    }
  }, [project, loadFiles]);

  const value: ProjectContextType = {
    project,
    files,
    stage,
    isConnected,
    isLoading,
    error,
    messages,
    isSending,
    agentStatuses,
    isTyping,
    sendMessage,
    loadProject,
    createProject,
    refreshFiles,
    setProject,
  };

  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
}

export function useProjectContext(): ProjectContextType {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return context;
}
