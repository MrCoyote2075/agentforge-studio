'use client';

import type { ProjectStage } from '@/types';

interface StageIndicatorProps {
  stage: ProjectStage;
}

const STAGES: { key: ProjectStage; label: string }[] = [
  { key: 'initialized', label: 'Started' },
  { key: 'requirements_gathering', label: 'Requirements' },
  { key: 'requirements_confirmed', label: 'Confirmed' },
  { key: 'planning', label: 'Planning' },
  { key: 'plan_approved', label: 'Approved' },
  { key: 'development', label: 'Development' },
  { key: 'development_complete', label: 'Built' },
  { key: 'review', label: 'Review' },
  { key: 'testing', label: 'Testing' },
  { key: 'ready_for_delivery', label: 'Ready' },
  { key: 'delivered', label: 'Delivered' },
];

export function StageIndicator({ stage }: StageIndicatorProps) {
  const currentIndex = STAGES.findIndex((s) => s.key === stage);

  return (
    <div className="flex items-center space-x-1 overflow-x-auto py-2">
      {STAGES.map((s, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <div key={s.key} className="flex items-center">
            <div
              className={`flex items-center justify-center rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                isCompleted
                  ? 'bg-success text-white'
                  : isCurrent
                  ? 'bg-primary text-white'
                  : 'bg-surface-light text-gray-400'
              }`}
            >
              {s.label}
            </div>
            {index < STAGES.length - 1 && (
              <div
                className={`h-0.5 w-3 ${
                  isCompleted ? 'bg-success' : 'bg-surface-light'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
