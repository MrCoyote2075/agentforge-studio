'use client';

import { useState, useCallback } from 'react';
import type { ChatMessage } from '@/types';
import * as api from '@/lib/api';

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string, projectId?: string) => Promise<void>;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  setMessages: (messages: ChatMessage[]) => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const sendMessage = useCallback(
    async (content: string, projectId?: string) => {
      setIsLoading(true);
      setError(null);

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMessage);

      try {
        if (projectId) {
          const response = await api.sendMessage(projectId, content);
          const agentMessage: ChatMessage = {
            id: (Date.now() + 1).toString(),
            role: 'agent',
            content: response.message,
            agent_name: 'Intermediator',
            timestamp: new Date().toISOString(),
          };
          addMessage(agentMessage);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send message');
      } finally {
        setIsLoading(false);
      }
    },
    [addMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    addMessage,
    clearMessages,
    setMessages,
  };
}
