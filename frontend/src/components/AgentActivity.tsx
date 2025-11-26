'use client';

import { useState } from 'react';
import { Users, ChevronDown, ChevronRight, Bot, Loader2 } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import type { AgentStatus } from '@/types';

const getStatusColor = (status: AgentStatus['status']) => {
  switch (status) {
    case 'busy':
      return 'bg-primary';
    case 'idle':
      return 'bg-gray-400';
    case 'waiting':
      return 'bg-warning';
    case 'error':
      return 'bg-error';
    default:
      return 'bg-gray-400';
  }
};

const getStatusIcon = (status: AgentStatus['status']) => {
  switch (status) {
    case 'busy':
      return <Loader2 className="h-3 w-3 animate-spin" />;
    default:
      return null;
  }
};

export function AgentActivity() {
  const { agentStatuses, project } = useProjectContext();
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Default agents when none are active
  const defaultAgents: AgentStatus[] = [
    { name: 'Intermediator', status: 'idle' },
    { name: 'Planner', status: 'idle' },
    { name: 'Frontend Agent', status: 'idle' },
    { name: 'Backend Agent', status: 'idle' },
    { name: 'Reviewer', status: 'idle' },
    { name: 'Tester', status: 'idle' },
  ];

  const agents = agentStatuses.length > 0 ? agentStatuses : defaultAgents;
  const activeCount = agents.filter((a) => a.status === 'busy').length;

  return (
    <div className="flex flex-col border-t border-surface-light bg-background">
      {/* Header */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between px-4 py-2 text-left transition-colors hover:bg-surface"
      >
        <div className="flex items-center space-x-2">
          <Users className="h-4 w-4 text-primary" />
          <span className="font-medium text-white">Agent Activity</span>
          {activeCount > 0 && (
            <span className="flex items-center space-x-1 rounded-full bg-primary px-2 py-0.5 text-xs text-white">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>{activeCount} active</span>
            </span>
          )}
        </div>
        {isCollapsed ? (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* Agent list */}
      {!isCollapsed && (
        <div className="max-h-48 overflow-y-auto border-t border-surface-light">
          {!project ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              No project selected
            </div>
          ) : (
            <ul className="py-1">
              {agents.map((agent) => (
                <li
                  key={agent.name}
                  className="flex items-center justify-between px-4 py-2"
                >
                  <div className="flex items-center space-x-2">
                    <Bot className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-300">{agent.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {agent.current_task && (
                      <span className="max-w-[150px] truncate text-xs text-gray-500">
                        {agent.current_task}
                      </span>
                    )}
                    <div className="flex items-center space-x-1">
                      {getStatusIcon(agent.status)}
                      <div
                        className={`h-2 w-2 rounded-full ${getStatusColor(
                          agent.status
                        )}`}
                      />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
