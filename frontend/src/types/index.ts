export interface Project {
  id: string;
  name: string;
  stage: ProjectStage;
  created_at: string;
  updated_at?: string;
  requirements: string;
  files: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  agent_name?: string;
  timestamp: string;
}

export interface GeneratedFile {
  path: string;
  content: string;
  file_type: string;
  created_by: string;
}

export type ProjectStage =
  | 'initialized'
  | 'requirements_gathering'
  | 'requirements_confirmed'
  | 'planning'
  | 'plan_approved'
  | 'development'
  | 'development_complete'
  | 'review'
  | 'testing'
  | 'ready_for_delivery'
  | 'delivered';

export interface AgentStatus {
  name: string;
  status: 'idle' | 'busy' | 'waiting' | 'error';
  current_task?: string;
}

export interface WebSocketMessage {
  type: string;
  payload: Record<string, unknown>;
}

export interface FileInfo {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
}

export interface ChatRequest {
  message: string;
  project_id?: string;
}

export interface ChatResponse {
  message: string;
  project_id?: string;
  agent_statuses?: AgentStatus[];
}
