'use client';

import { useState, useRef, useCallback } from 'react';

interface DecisionPanelProps {
  visible: boolean;
  onDecision: (decision: string) => void;
  protocolNumber: string;
}

export default function DecisionPanel({ visible, onDecision, protocolNumber }: DecisionPanelProps) {
  const [decided, setDecided] = useState(false);
  const [chosenDecision, setChosenDecision] = useState('');
  const [rippleStyle, setRippleStyle] = useState<Record<string, React.CSSProperties>>({});
  const panelRef = useRef<HTMLDivElement>(null);

  const handleRipple = useCallback((e: React.MouseEvent<HTMLButtonElement>, key: string) => {
    const button = e.currentTarget;
    const rect = button.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setRippleStyle((prev) => ({
      ...prev,
      [key]: {
        left: x,
        top: y,
        opacity: 1,
      },
    }));
    setTimeout(() => {
      setRippleStyle((prev) => ({
        ...prev,
        [key]: { ...prev[key], opacity: 0 },
      }));
    }, 600);
  }, []);

  const handleDecision = (decision: string, e: React.MouseEvent<HTMLButtonElement>) => {
    handleRipple(e, decision);
    setChosenDecision(decision);
    setDecided(true);
    setTimeout(() => {
      onDecision(decision);
    }, 1000);
  };

  const decisions = [
    {
      key: 'approve',
      label: 'Approve',
      sublabel: 'Protocol meets all requirements',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      colors: {
        bg: 'bg-emerald-500/10 hover:bg-emerald-500/20',
        border: 'border-emerald-500/30 hover:border-emerald-500/60',
        text: 'text-emerald-400',
        glow: 'hover:shadow-[0_0_30px_-5px_rgba(16,185,129,0.4)]',
        ripple: 'bg-emerald-400/30',
      },
    },
    {
      key: 'revisions',
      label: 'Request Revisions',
      sublabel: 'Return for modifications',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
        </svg>
      ),
      colors: {
        bg: 'bg-amber-500/10 hover:bg-amber-500/20',
        border: 'border-amber-500/30 hover:border-amber-500/60',
        text: 'text-amber-400',
        glow: 'hover:shadow-[0_0_30px_-5px_rgba(245,158,11,0.4)]',
        ripple: 'bg-amber-400/30',
      },
    },
    {
      key: 'reject',
      label: 'Reject',
      sublabel: 'Protocol does not meet standards',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      ),
      colors: {
        bg: 'bg-red-500/10 hover:bg-red-500/20',
        border: 'border-red-500/30 hover:border-red-500/60',
        text: 'text-red-400',
        glow: 'hover:shadow-[0_0_30px_-5px_rgba(239,68,68,0.4)]',
        ripple: 'bg-red-400/30',
      },
    },
  ];

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className={`
          absolute inset-0 bg-black/60 backdrop-blur-sm
          transition-opacity duration-500
          ${visible ? 'opacity-100' : 'opacity-0'}
        `}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={`
          relative w-full max-w-lg
          bg-[#111128]/95 backdrop-blur-2xl
          rounded-2xl border border-[#2a2a5a]/80
          shadow-2xl shadow-indigo-500/10
          transition-all duration-500 ease-out
          ${visible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-90 translate-y-8'}
        `}
      >
        {/* Top accent */}
        <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-2xl bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500" />

        {/* Glow effects */}
        <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-64 h-32 bg-indigo-500/10 rounded-full blur-3xl" />

        <div className="relative p-6">
          {!decided ? (
            <>
              {/* Header */}
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-600/30 to-purple-600/20 border border-indigo-500/30 mb-4">
                  <span className="text-3xl">🏛️</span>
                </div>
                <h2 className="text-xl font-bold text-white mb-1">
                  IRB Chair Decision Required
                </h2>
                <p className="text-sm text-slate-400">
                  Protocol cannot proceed without your decision
                </p>
                <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                  <span className="text-xs font-mono text-slate-300">{protocolNumber}</span>
                </div>
              </div>

              {/* Decision Buttons */}
              <div className="space-y-3">
                {decisions.map((d) => (
                  <button
                    key={d.key}
                    onClick={(e) => handleDecision(d.key, e)}
                    className={`
                      relative w-full overflow-hidden
                      flex items-center gap-4 p-4 rounded-xl
                      border transition-all duration-300
                      ${d.colors.bg} ${d.colors.border} ${d.colors.glow}
                      group
                    `}
                  >
                    {/* Ripple effect */}
                    <span
                      className={`absolute w-[300px] h-[300px] rounded-full -translate-x-1/2 -translate-y-1/2 ${d.colors.ripple} pointer-events-none transition-all duration-700 ${
                        rippleStyle[d.key]?.opacity ? 'scale-100 opacity-0' : 'scale-0 opacity-100'
                      }`}
                      style={{
                        left: rippleStyle[d.key]?.left,
                        top: rippleStyle[d.key]?.top,
                      }}
                    />

                    <div className={`relative flex-shrink-0 ${d.colors.text} transition-transform duration-300 group-hover:scale-110`}>
                      {d.icon}
                    </div>
                    <div className="relative text-left">
                      <p className={`text-sm font-bold ${d.colors.text}`}>{d.label}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{d.sublabel}</p>
                    </div>
                    <svg
                      className={`relative ml-auto w-4 h-4 ${d.colors.text} opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-[-8px] group-hover:translate-x-0`}
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </button>
                ))}
              </div>

              {/* Disclaimer */}
              <p className="mt-4 text-center text-[10px] text-slate-600">
                This decision is binding and will be recorded in the audit trail
              </p>
            </>
          ) : (
            /* Confirmation State */
            <div className="text-center py-8">
              <div className={`
                inline-flex items-center justify-center w-16 h-16 rounded-full mb-4
                transition-all duration-500 animate-[scaleIn_0.5s_ease-out]
                ${chosenDecision === 'approve' ? 'bg-emerald-500/20 border-2 border-emerald-500/50' : ''}
                ${chosenDecision === 'revisions' ? 'bg-amber-500/20 border-2 border-amber-500/50' : ''}
                ${chosenDecision === 'reject' ? 'bg-red-500/20 border-2 border-red-500/50' : ''}
              `}>
                {chosenDecision === 'approve' && (
                  <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
                {chosenDecision === 'revisions' && (
                  <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                  </svg>
                )}
                {chosenDecision === 'reject' && (
                  <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </div>

              <h3 className="text-lg font-bold text-white mb-1">Decision Recorded</h3>
              <p className="text-sm text-slate-400 mb-2">
                {chosenDecision === 'approve' && 'Protocol has been approved'}
                {chosenDecision === 'revisions' && 'Protocol returned for revisions'}
                {chosenDecision === 'reject' && 'Protocol has been rejected'}
              </p>
              <div className="flex items-center justify-center gap-2 text-[10px] text-slate-500">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Transmitting to committee agents...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
