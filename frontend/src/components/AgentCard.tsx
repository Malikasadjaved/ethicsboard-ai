'use client';

import { useEffect, useState } from 'react';

interface AgentCardProps {
  name: string;
  framework: string;
  model: string;
  provider: string;
  status: 'idle' | 'active' | 'complete' | 'error';
  icon: string;
  color: string;
}

export default function AgentCard({ name, framework, model, provider, status, icon, color }: AgentCardProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const statusConfig = {
    idle: {
      border: 'border-slate-700/50',
      bg: 'bg-slate-900/30',
      glow: '',
      label: 'Standby',
      labelColor: 'text-slate-500',
      dotColor: 'bg-slate-600',
      opacity: 'opacity-60',
    },
    active: {
      border: `border-[${color}]/50`,
      bg: 'bg-[#111128]/60',
      glow: `shadow-[0_0_30px_-5px_${color}40]`,
      label: 'Analyzing...',
      labelColor: 'text-white',
      dotColor: `bg-[${color}]`,
      opacity: 'opacity-100',
    },
    complete: {
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-950/20',
      glow: 'shadow-[0_0_20px_-5px_rgba(16,185,129,0.2)]',
      label: 'Complete',
      labelColor: 'text-emerald-400',
      dotColor: 'bg-emerald-400',
      opacity: 'opacity-100',
    },
    error: {
      border: 'border-red-500/40',
      bg: 'bg-red-950/20',
      glow: 'shadow-[0_0_20px_-5px_rgba(239,68,68,0.3)]',
      label: 'Error',
      labelColor: 'text-red-400',
      dotColor: 'bg-red-400',
      opacity: 'opacity-100',
    },
  };

  const config = statusConfig[status];

  return (
    <div
      className={`
        relative group rounded-xl p-4 backdrop-blur-md transition-all duration-500
        border ${config.opacity}
        ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
      `}
      style={{
        borderColor: status === 'active' ? `${color}50` : status === 'complete' ? 'rgba(16,185,129,0.3)' : status === 'error' ? 'rgba(239,68,68,0.4)' : 'rgba(51,51,90,0.5)',
        backgroundColor: status === 'active' ? 'rgba(17,17,40,0.6)' : status === 'complete' ? 'rgba(5,46,22,0.2)' : status === 'error' ? 'rgba(69,10,10,0.2)' : 'rgba(15,15,35,0.3)',
        boxShadow: status === 'active' ? `0 0 30px -5px ${color}40` : status === 'complete' ? '0 0 20px -5px rgba(16,185,129,0.2)' : 'none',
      }}
    >
      {/* Active glow animation */}
      {status === 'active' && (
        <>
          <div
            className="absolute inset-0 rounded-xl animate-pulse opacity-20"
            style={{ boxShadow: `inset 0 0 40px -10px ${color}` }}
          />
          <div
            className="absolute -inset-[1px] rounded-xl opacity-30 animate-[spin_8s_linear_infinite]"
            style={{
              background: `conic-gradient(from 0deg, transparent, ${color}, transparent, transparent)`,
              mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
              maskComposite: 'xor',
              WebkitMaskComposite: 'xor',
              padding: '1px',
            }}
          />
        </>
      )}

      <div className="relative z-10">
        {/* Top Row: Icon + Status */}
        <div className="flex items-start justify-between mb-3">
          {/* Agent Icon */}
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl border transition-all duration-300"
            style={{
              backgroundColor: `${color}15`,
              borderColor: `${color}30`,
            }}
          >
            {icon}
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-1.5">
            <span className={`relative flex h-2 w-2`}>
              {(status === 'active') && (
                <span
                  className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping"
                  style={{ backgroundColor: color }}
                />
              )}
              <span
                className="relative inline-flex rounded-full h-2 w-2"
                style={{
                  backgroundColor: status === 'active' ? color : status === 'complete' ? '#10b981' : status === 'error' ? '#ef4444' : '#475569',
                }}
              />
            </span>
            <span
              className={`text-[10px] font-semibold uppercase tracking-wider ${config.labelColor}`}
            >
              {config.label}
            </span>
          </div>
        </div>

        {/* Agent Name */}
        <h3 className="text-sm font-bold text-white mb-1 tracking-wide">{name}</h3>

        {/* Framework & Model Badges */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <span
            className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest rounded-md border backdrop-blur-sm"
            style={{
              backgroundColor: `${color}10`,
              borderColor: `${color}25`,
              color: color,
            }}
          >
            {framework}
          </span>
          <span className="px-2 py-0.5 text-[9px] font-medium text-slate-400 bg-slate-800/50 rounded-md border border-slate-700/50">
            {model}
          </span>
        </div>

        {/* Provider */}
        <div className="flex items-center gap-1 text-[10px] text-slate-500">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
          </svg>
          <span>{provider}</span>
        </div>

        {/* Active Typing Indicator */}
        {status === 'active' && (
          <div className="mt-3 flex items-center gap-1.5">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: '0ms', animationDuration: '1.2s' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: '200ms', animationDuration: '1.2s' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: '400ms', animationDuration: '1.2s' }} />
            </div>
            <span className="text-[10px] font-medium" style={{ color: `${color}cc` }}>
              Processing...
            </span>
          </div>
        )}

        {/* Complete Checkmark */}
        {status === 'complete' && (
          <div className="mt-3 flex items-center gap-1.5">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
              Review Submitted
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
