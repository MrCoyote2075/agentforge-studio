'use client';

interface TypingIndicatorProps {
  agentName?: string;
}

export function TypingIndicator({ agentName = 'Agent' }: TypingIndicatorProps) {
  return (
    <div className="flex items-center space-x-2 px-4 py-2">
      <div className="flex items-center space-x-3 rounded-lg bg-surface px-4 py-3">
        <span className="text-sm text-gray-400">{agentName} is typing</span>
        <div className="flex space-x-1">
          <div
            className="h-2 w-2 animate-bounce rounded-full bg-primary"
            style={{ animationDelay: '0ms' }}
          />
          <div
            className="h-2 w-2 animate-bounce rounded-full bg-primary"
            style={{ animationDelay: '150ms' }}
          />
          <div
            className="h-2 w-2 animate-bounce rounded-full bg-primary"
            style={{ animationDelay: '300ms' }}
          />
        </div>
      </div>
    </div>
  );
}
