import type { Project, ChatResponse, FileInfo } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

export async function createProject(
  name: string,
  requirements: string
): Promise<Project> {
  return fetchApi<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({ name, requirements }),
  });
}

export async function sendMessage(
  projectId: string,
  message: string
): Promise<ChatResponse> {
  return fetchApi<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, project_id: projectId }),
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return fetchApi<Project>(`/projects/${projectId}`);
}

export async function listProjects(): Promise<Project[]> {
  return fetchApi<Project[]>('/projects');
}

export async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${API_URL}/projects/${projectId}`, {
    method: 'DELETE',
  });
}

export async function getFiles(projectId: string): Promise<FileInfo[]> {
  return fetchApi<FileInfo[]>(`/projects/${projectId}/files?recursive=true`);
}

export async function getFileContent(
  projectId: string,
  filePath: string
): Promise<{ path: string; content: string }> {
  return fetchApi<{ path: string; content: string }>(
    `/projects/${projectId}/files/${filePath}`
  );
}

export async function downloadZip(projectId: string): Promise<Blob> {
  const response = await fetch(`${API_URL}/projects/${projectId}/download`);
  if (!response.ok) {
    throw new Error('Failed to download project');
  }
  return response.blob();
}

export function getWebSocketUrl(projectId?: string): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = process.env.NEXT_PUBLIC_WS_URL || 'localhost:8000';
  if (projectId) {
    return `${wsProtocol}//${wsHost}/ws/project/${projectId}`;
  }
  return `${wsProtocol}//${wsHost}/ws`;
}
