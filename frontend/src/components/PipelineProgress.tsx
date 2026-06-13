'use client';

import { useEffect, useState } from 'react';

type PipelineStage = 'pending' | 'protocol_review' | 'ethics_review' | 'privacy_review' | 'committee_review' | 'awaiting_chair' | 'completed';

interface PipelineProgressProps {
  currentStage: PipelineStage;
}

interface StageConfig {
  id: string;
  label: string;
  icon: string;
  activeColor: string;
  glowColor: string;
}

const stages: StageConfig[] = [
  {
    id: 'protocol_review',
    label: 'Protocol Analysis',
    icon: '📋',
    activeColor: '#6366f1',
    glowColor: 'rgba(99, 102, 241, 0.3)',
  },
  {
    id: 'ethics_review',
    label: 'Ethics Review',
    icon: '⚖️',
    activeColor: '#a855f7',
    glowColor: 'rgba(168, 85, 247, 0.3)',
  },
  {
    id: 'privacy_review',
    label: 'Privacy Review',
    icon: '🔒',
    activeColor: '#06b6d4',
    glowColor: 'rgba(6, 182, 212, 0.3)',
  },
  {
    id: 'committee_review',
    label: 'Committee Decision',
    icon: '🏛️',
    activeColor: '#f59e0b',
    glowColor: 'rgba(245, 158, 11, 0.3)',
  },
];

function getStageStatus(stageId: string, currentStage: PipelineStage): 'pending' | 'active' | 'complete' {
  const stageOrder = ['protocol_review', 'ethics_review', 'privacy_review', 'committee_review'];
  const currentIndex = stageOrder.indexOf(currentStage);
  const stageIndex = stageOrder.indexOf(stageId);

  if (currentStage === 'completed') return 'complete';
  if (currentStage === 'pending') return 'pending';
  if (currentStage === 'awaiting_chair') {
    // All stages complete except committee is active
    if (stageId === 'committee_review') return 'active';
    return 'complete';
  }

  if (stageIndex < currentIndex) return 'complete';
  if (stageIndex === currentIndex) return 'active';
  return 'pending';
}

export default function PipelineProgress({ currentStage }: PipelineProgressProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="w-full rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <span className="text-base">🔄</span>
          <h2 className="text-sm font-bold text-white tracking-wide">Review Pipeline</h2>
        </div>
        <span className={`
          px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest rounded-full border
          ${currentStage === 'completed'
            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
            : currentStage === 'pending'
              ? 'bg-slate-500/15 text-slate-400 border-slate-500/30'
              : 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
          }
        `}>
          {currentStage === 'completed' ? 'Complete' : currentStage === 'pending' ? 'Ready' : 'In Progress'}
        </span>
      </div>

      {/* Pipeline Visualization */}
      <div className="p-4 sm:p-6">
        {/* Desktop: Horizontal */}
        <div className="hidden sm:flex items-center justify-between relative">
          {/* Connecting Line Background */}
          <div className="absolute top-6 left-[40px] right-[40px] h-[2px] bg-[#1e1e3a]" />

          {/* Connecting Line Progress */}
          <div
            className="absolute top-6 left-[40px] h-[2px] bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-1000 ease-out"
            style={{
              width: (() => {
                const stageOrder = ['protocol_review', 'ethics_review', 'privacy_review', 'committee_review'];
                const currentIndex = stageOrder.indexOf(currentStage);
                if (currentStage === 'completed') return 'calc(100% - 80px)';
                if (currentStage === 'pending') return '0%';
                if (currentStage === 'awaiting_chair') return 'calc(100% - 80px)';
                const totalSegments = stageOrder.length - 1;
                const completedSegments = currentIndex;
                return `calc(${(completedSegments / totalSegments) * 100}% - ${80 * (completedSegments / totalSegments)}px)`;
              })(),
            }}
          />

          {stages.map((stage, index) => {
            const status = getStageStatus(stage.id, currentStage);
            const isLast = index === stages.length - 1;

            return (
              <div
                key={stage.id}
                className={`
                  relative flex flex-col items-center gap-2 z-10
                  transition-all duration-700 ease-out
                  ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
                `}
                style={{ transitionDelay: `${index * 150}ms`, flex: '1' }}
              >
                {/* Stage Circle */}
                <div className="relative">
                  {/* Active glow */}
                  {status === 'active' && (
                    <div
                      className="absolute inset-[-4px] rounded-full animate-pulse"
                      style={{ boxShadow: `0 0 20px ${stage.glowColor}` }}
                    />
                  )}

                  <div
                    className={`
                      w-12 h-12 rounded-full flex items-center justify-center
                      border-2 transition-all duration-500
                      ${status === 'complete'
                        ? 'bg-emerald-500/20 border-emerald-500/50'
                        : status === 'active'
                          ? 'border-2'
                          : 'bg-[#111128]/60 border-[#2a2a5a]/50'
                      }
                    `}
                    style={status === 'active' ? {
                      backgroundColor: `${stage.activeColor}15`,
                      borderColor: `${stage.activeColor}60`,
                    } : {}}
                  >
                    {status === 'complete' ? (
                      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : (
                      <span className={`text-lg ${status === 'pending' ? 'opacity-40 grayscale' : ''}`}>
                        {stage.icon}
                      </span>
                    )}
                  </div>

                  {/* Active progress ring */}
                  {status === 'active' && (
                    <svg className="absolute inset-[-3px] w-[calc(100%+6px)] h-[calc(100%+6px)] animate-[spin_3s_linear_infinite]" viewBox="0 0 54 54">
                      <circle
                        cx="27"
                        cy="27"
                        r="25"
                        fill="none"
                        strokeWidth="2"
                        strokeDasharray="25 130"
                        strokeLinecap="round"
                        style={{ stroke: stage.activeColor }}
                      />
                    </svg>
                  )}
                </div>

                {/* Stage Label */}
                <span className={`
                  text-[11px] font-semibold text-center leading-tight transition-colors duration-500
                  ${status === 'complete' ? 'text-emerald-400' : status === 'active' ? 'text-white' : 'text-slate-600'}
                `}>
                  {stage.label}
                </span>

                {/* Status text */}
                <span className={`
                  text-[9px] font-mono uppercase tracking-wider transition-colors duration-500
                  ${status === 'complete' ? 'text-emerald-500/60' : status === 'active' ? 'text-indigo-400/60' : 'text-slate-700'}
                `}>
                  {status === 'complete' ? '✓ Done' : status === 'active' ? '● Active' : '○ Pending'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Mobile: Vertical */}
        <div className="flex sm:hidden flex-col gap-1">
          {stages.map((stage, index) => {
            const status = getStageStatus(stage.id, currentStage);
            const isLast = index === stages.length - 1;

            return (
              <div key={stage.id}>
                <div
                  className={`
                    flex items-center gap-3 p-3 rounded-lg transition-all duration-500
                    ${status === 'active' ? 'bg-[#111128]/60' : ''}
                  `}
                  style={status === 'active' ? {
                    boxShadow: `inset 0 0 20px ${stage.glowColor}`,
                    border: `1px solid ${stage.activeColor}30`,
                  } : {}}
                >
                  {/* Circle */}
                  <div className="relative flex-shrink-0">
                    {status === 'active' && (
                      <div
                        className="absolute inset-[-3px] rounded-full animate-pulse"
                        style={{ boxShadow: `0 0 15px ${stage.glowColor}` }}
                      />
                    )}
                    <div
                      className={`
                        w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500
                        ${status === 'complete'
                          ? 'bg-emerald-500/20 border-emerald-500/50'
                          : status === 'pending'
                            ? 'bg-[#111128]/60 border-[#2a2a5a]/50'
                            : ''
                        }
                      `}
                      style={status === 'active' ? {
                        backgroundColor: `${stage.activeColor}15`,
                        borderColor: `${stage.activeColor}60`,
                      } : {}}
                    >
                      {status === 'complete' ? (
                        <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      ) : (
                        <span className={`text-base ${status === 'pending' ? 'opacity-40 grayscale' : ''}`}>
                          {stage.icon}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Text */}
                  <div className="flex-1">
                    <p className={`text-xs font-bold transition-colors duration-500 ${
                      status === 'complete' ? 'text-emerald-400' : status === 'active' ? 'text-white' : 'text-slate-600'
                    }`}>
                      {stage.label}
                    </p>
                    <p className={`text-[9px] font-mono uppercase tracking-wider ${
                      status === 'complete' ? 'text-emerald-500/60' : status === 'active' ? 'text-indigo-400/60' : 'text-slate-700'
                    }`}>
                      {status === 'complete' ? 'Completed' : status === 'active' ? 'In Progress' : 'Pending'}
                    </p>
                  </div>

                  {/* Active indicator */}
                  {status === 'active' && (
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: stage.activeColor, animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: stage.activeColor, animationDelay: '200ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: stage.activeColor, animationDelay: '400ms' }} />
                    </div>
                  )}
                </div>

                {/* Vertical connector */}
                {!isLast && (
                  <div className="flex justify-start pl-[18px] py-0">
                    <div className={`w-[2px] h-3 transition-colors duration-500 ${
                      getStageStatus(stages[index + 1].id, currentStage) !== 'pending' || status === 'complete'
                        ? 'bg-emerald-500/40'
                        : 'bg-[#1e1e3a]'
                    }`} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
