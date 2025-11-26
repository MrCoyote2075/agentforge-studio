'use client';

import type { ChatMessage } from '@/types';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div
        className={`flex max-w-[80%] ${
          isUser ? 'flex-row-reverse' : 'flex-row'
        } items-start gap-2`}
      >
        {/* Avatar */}
        <div
          className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${
            isUser ? 'bg-primary' : 'bg-surface-light'
          }`}
        >
          {isUser ? (
            <User className="h-4 w-4 text-white" />
          ) : (
            <Bot className="h-4 w-4 text-gray-300" />
          )}
        </div>

        {/* Message content */}
        <div className="flex flex-col">
          {!isUser && message.agent_name && (
            <span className="mb-1 text-xs text-gray-400">
              {message.agent_name}
            </span>
          )}
          <div
            className={`rounded-lg px-4 py-2 ${
              isUser
                ? 'bg-primary text-white'
                : 'bg-surface text-gray-100'
            }`}
          >
            <p className="whitespace-pre-wrap text-sm">{message.content}</p>
          </div>
          <span
            className={`mt-1 text-xs text-gray-500 ${
              isUser ? 'text-right' : 'text-left'
            }`}
          >
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}
