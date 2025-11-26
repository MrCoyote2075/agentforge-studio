'use client';

import { useRef, useEffect, useState, type FormEvent } from 'react';
import { Send, MessageSquare } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

export function ChatPanel() {
  const { messages, isTyping, isSending, sendMessage, project } =
    useProjectContext();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const message = input.trim();
    setInput('');
    await sendMessage(message);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex h-full flex-col border-r border-surface-light bg-background">
      {/* Chat header */}
      <div className="flex items-center space-x-2 border-b border-surface-light px-4 py-3">
        <MessageSquare className="h-5 w-5 text-primary" />
        <h2 className="font-semibold text-white">Chat</h2>
        <span className="text-xs text-gray-400">
          ({messages.length} messages)
        </span>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <MessageSquare className="mb-4 h-12 w-12 text-gray-500" />
            <p className="text-gray-400">
              {project
                ? 'Start a conversation with the AI agents'
                : 'Create or select a project to start chatting'}
            </p>
            <p className="mt-2 text-sm text-gray-500">
              Describe what you want to build and the agents will help you
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator agentName="Intermediator" />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-surface-light p-4"
      >
        <div className="flex items-end space-x-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              project
                ? 'Type your message... (Enter to send, Shift+Enter for new line)'
                : 'Create a project first...'
            }
            disabled={!project || isSending}
            className="max-h-32 min-h-[44px] flex-1 resize-none rounded-lg border border-surface-light bg-surface px-4 py-2 text-white placeholder-gray-500 focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            rows={1}
          />
          <button
            type="submit"
            disabled={!input.trim() || !project || isSending}
            className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Send message"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
