'use client';

import { useEffect, useState } from 'react';

interface Deficiency {
  id: number;
  title: string;
  severity: string;
  regulation: string;
  description: string;
}

interface DeficiencyPanelProps {
  deficiencies: Deficiency[];
}

export default function DeficiencyPanel({ deficiencies }: DeficiencyPanelProps) {
  const [animatedIds, setAnimatedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    deficiencies.forEach((def, index) => {
      if (!animatedIds.has(def.id)) {
        setTimeout(() => {
          setAnimatedIds((prev) => new Set([...prev, def.id]));
        }, index * 150);
      }
    });
  }, [deficiencies]);

  const criticalCount = deficiencies.filter((d) => d.severity === 'critical').length;
  const majorCount = deficiencies.filter((d) => d.severity === 'major').length;

  return (
    <div className="flex flex-col h-full rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <span className="text-base">🚨</span>
          <h2 className="text-sm font-bold text-white tracking-wide">Deficiencies</h2>
        </div>
        {deficiencies.length > 0 ? (
          <div className="flex items-center gap-2">
            {criticalCount > 0 && (
              <span className="px-2 py-0.5 text-[10px] font-bold bg-red-500/20 text-red-400 rounded-full border border-red-500/30">
                {criticalCount} Critical
              </span>
            )}
            {majorCount > 0 && (
              <span className="px-2 py-0.5 text-[10px] font-bold bg-orange-500/20 text-orange-400 rounded-full border border-orange-500/30">
                {majorCount} Major
              </span>
            )}
          </div>
        ) : (
          <span className="text-[10px] text-slate-500 font-mono">MONITORING</span>
        )}
      </div>

      {/* Count Banner */}
      {deficiencies.length > 0 && (
        <div className="px-4 py-2 bg-red-950/20 border-b border-red-500/10">
          <div className="flex items-center gap-2">
            <div className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-400" />
            </div>
            <span className="text-xs font-bold text-red-300">
              {deficiencies.length} Deficienc{deficiencies.length === 1 ? 'y' : 'ies'} Detected
            </span>
          </div>
        </div>
      )}

      {/* Deficiency Cards */}
      <div
        className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#334155 transparent',
        }}
      >
        {deficiencies.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            {/* Shimmer placeholder cards */}
            <div className="w-full space-y-3 mb-6">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="relative overflow-hidden rounded-lg p-4 bg-slate-800/20 border border-slate-700/20"
                >
                  <div className="space-y-2">
                    <div className="h-3 w-20 rounded bg-slate-700/30" />
                    <div className="h-2 w-3/4 rounded bg-slate-700/20" />
                    <div className="h-2 w-1/2 rounded bg-slate-700/15" />
                  </div>
                  {/* Shimmer sweep */}
                  <div
                    className="absolute inset-0 -translate-x-full animate-[shimmer_2.5s_infinite]"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.02), transparent)',
                    }}
                  />
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500 font-medium">Awaiting agent review...</p>
            <p className="text-[10px] text-slate-600 mt-1">Deficiencies will appear as agents analyze the protocol</p>
          </div>
        )}

        {deficiencies.map((def, index) => {
          const isCritical = def.severity === 'critical';
          const isVisible = animatedIds.has(def.id);

          return (
            <div
              key={def.id}
              className={`
                group relative rounded-lg overflow-hidden
                transition-all duration-500 ease-out
                ${isVisible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-6 scale-95'}
              `}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              {/* Severity Left Border */}
              <div
                className={`absolute left-0 top-0 bottom-0 w-1 ${
                  isCritical ? 'bg-red-500' : 'bg-orange-500'
                }`}
              />

              <div
                className={`
                  p-3.5 pl-4 border transition-all duration-300
                  ${isCritical
                    ? 'bg-red-950/25 border-red-500/20 hover:border-red-500/40 hover:bg-red-950/35'
                    : 'bg-orange-950/15 border-orange-500/15 hover:border-orange-500/30 hover:bg-orange-950/25'
                  }
                  rounded-lg
                `}
              >
                {/* Top: Severity + ID */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`
                        px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded-md border
                        ${isCritical
                          ? 'bg-red-500/20 text-red-400 border-red-500/30'
                          : 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                        }
                      `}
                    >
                      {def.severity}
                    </span>
                    <span className="text-[10px] text-slate-600 font-mono">#{def.id}</span>
                  </div>
                  {isCritical && (
                    <span className="text-red-400 animate-pulse">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                      </svg>
                    </span>
                  )}
                </div>

                {/* Title */}
                <h4 className={`text-sm font-bold mb-1.5 ${isCritical ? 'text-red-200' : 'text-orange-200'}`}>
                  {def.title}
                </h4>

                {/* Regulation */}
                <div className="flex items-center gap-1.5 mb-2">
                  <svg className="w-3 h-3 text-slate-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                  </svg>
                  <span className="text-[10px] text-slate-400 font-mono">{def.regulation}</span>
                </div>

                {/* Description */}
                <p className="text-[11px] text-slate-400 leading-relaxed">{def.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom accent */}
      <div className={`h-1 transition-all duration-500 ${
        deficiencies.length > 0
          ? criticalCount > 0
            ? 'bg-gradient-to-r from-transparent via-red-500/40 to-transparent'
            : 'bg-gradient-to-r from-transparent via-orange-500/30 to-transparent'
          : 'bg-gradient-to-r from-transparent via-slate-700/20 to-transparent'
      }`} />
    </div>
  );
}
