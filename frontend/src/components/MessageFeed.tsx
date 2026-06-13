'use client';

import { useEffect, useRef, useState } from 'react';

interface Deficiency {
  id: number;
  title: string;
  severity: string;
  regulation: string;
  description: string;
}

interface Message {
  id: string;
  timestamp: string;
  agent: string;
  framework: string;
  model_provider: string;
  content: string;
  message_type: string;
  deficiencies?: Deficiency[];
}

interface MessageFeedProps {
  messages: Message[];
}

const agentColors: Record<string, string> = {
  ProtocolAgent: '#6366f1',
  EthicsAgent: '#a855f7',
  PrivacyAgent: '#06b6d4',
  CommitteeAgent: '#f59e0b',
  System: '#64748b',
};

const agentIcons: Record<string, string> = {
  ProtocolAgent: '📋',
  EthicsAgent: '⚖️',
  PrivacyAgent: '🔒',
  CommitteeAgent: '🏛️',
  System: '⚙️',
};

function formatTimestamp(ts: string) {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts;
  }
}

// Friendly fallback for any Band-rewritten mention (@[[uuid]]) the backend
// didn't already prettify
function normalizeMentions(content: string): string {
  return content.replace(/@\[\[[0-9a-fA-F-]+\]\]/g, '@agent');
}

function highlightContent(content: string) {
  // Highlight @mentions (handles like @ethics_agent and @Dr.IRBChair)
  const parts = normalizeMentions(content).split(/(@[\w.]+)/g);
  return parts.map((part, i) => {
    if (part.startsWith('@')) {
      return (
        <span key={i} className="text-indigo-400 font-semibold bg-indigo-500/10 px-1 rounded">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

type ChallengeKind = 'request' | 'response' | null;

function getChallengeKind(content: string): ChallengeKind {
  const stripped = content.trimStart();
  if (stripped.startsWith('CLARIFICATION REQUEST')) return 'request';
  if (stripped.startsWith('CLARIFICATION RESPONSE')) return 'response';
  return null;
}

function getMessageBorderType(content: string, messageType: string): 'deficiency' | 'pass' | 'challenge' | 'none' {
  // The agent-to-agent challenge exchange gets its own styling — it mentions
  // "blocking deficiency" but is coordination, not a new finding
  if (getChallengeKind(content)) return 'challenge';
  const lower = content.toLowerCase();
  if (messageType === 'deficiency' || lower.includes('deficiency') || lower.includes('violation') || lower.includes('non-compliant') || lower.includes('critical')) {
    return 'deficiency';
  }
  if (lower.includes('pass') || lower.includes('compliant') || lower.includes('approved') || lower.includes('no issues')) {
    return 'pass';
  }
  return 'none';
}

export default function MessageFeed({ messages }: MessageFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null);
  const [visibleMessages, setVisibleMessages] = useState<Set<string>>(new Set());

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages]);

  // Animate messages in
  useEffect(() => {
    const newIds = new Set(visibleMessages);
    messages.forEach((msg) => {
      if (!newIds.has(msg.id)) {
        setTimeout(() => {
          setVisibleMessages((prev) => new Set([...prev, msg.id]));
        }, 50);
      }
    });
  }, [messages]);

  return (
    <div className="flex flex-col h-full rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <h2 className="text-sm font-bold text-white tracking-wide">Band Room</h2>
          <span className="text-[10px] text-slate-500 font-mono">LIVE</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {messages.length} messages
        </span>
      </div>

      {/* Messages Container */}
      <div
        ref={feedRef}
        className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#334155 transparent',
        }}
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 rounded-2xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mb-4 animate-pulse">
              <span className="text-3xl opacity-50">💬</span>
            </div>
            <p className="text-sm text-slate-500 font-medium">Waiting for agents to begin...</p>
            <p className="text-xs text-slate-600 mt-1">Messages will appear here in real-time</p>
          </div>
        )}

        {messages.map((msg, index) => {
          const color = agentColors[msg.agent] || '#64748b';
          const agentIcon = agentIcons[msg.agent] || '🤖';
          const borderType = getMessageBorderType(msg.content, msg.message_type);
          const challengeKind = getChallengeKind(msg.content);
          const isVisible = visibleMessages.has(msg.id);

          return (
            <div
              key={msg.id}
              className={`
                relative group transition-all duration-500 ease-out
                ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
              `}
              style={{ transitionDelay: `${Math.min(index * 30, 300)}ms` }}
            >
              <div
                className={`
                  relative rounded-lg p-3 transition-all duration-300
                  bg-[#111128]/40 hover:bg-[#151535]/60
                  ${borderType === 'deficiency' ? 'border-l-2 border-l-red-500/70' : ''}
                  ${borderType === 'pass' ? 'border-l-2 border-l-emerald-500/70' : ''}
                  ${borderType === 'challenge' ? 'border-l-2 border-l-amber-500/70 bg-amber-950/10' : ''}
                  ${borderType === 'none' ? 'border-l-2 border-l-transparent' : ''}
                `}
              >
                {/* Agent-to-agent challenge banner */}
                {challengeKind && (
                  <div className="flex items-center gap-2 mb-2 -mt-0.5">
                    <span className={`
                      inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase tracking-widest
                      ${challengeKind === 'request'
                        ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                        : 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                      }
                    `}>
                      {challengeKind === 'request' ? '⚔️ Agent Challenge' : '🛡️ Challenge Response'}
                    </span>
                    <span className="text-[9px] text-slate-500 font-mono">
                      {challengeKind === 'request' ? 'Committee → Ethics' : 'Ethics → Committee'}
                    </span>
                  </div>
                )}
                {/* Message Header */}
                <div className="flex items-center gap-2 mb-2">
                  {/* Agent Avatar */}
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0 border"
                    style={{
                      backgroundColor: `${color}15`,
                      borderColor: `${color}30`,
                    }}
                  >
                    {agentIcon}
                  </div>

                  {/* Agent Name */}
                  <span
                    className="text-xs font-bold tracking-wide"
                    style={{ color }}
                  >
                    {msg.agent}
                  </span>

                  {/* Framework Badge */}
                  <span
                    className="px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-widest rounded border"
                    style={{
                      backgroundColor: `${color}10`,
                      borderColor: `${color}20`,
                      color: `${color}aa`,
                    }}
                  >
                    {msg.framework}
                  </span>

                  {/* Timestamp */}
                  <span className="ml-auto text-[10px] text-slate-600 font-mono opacity-0 group-hover:opacity-100 transition-opacity">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>

                {/* Message Content */}
                <div className="text-[13px] text-slate-300 leading-relaxed pl-9">
                  {highlightContent(msg.content)}
                </div>

                {/* Inline Deficiencies */}
                {msg.deficiencies && msg.deficiencies.length > 0 && (
                  <div className="mt-3 pl-9 space-y-2">
                    {msg.deficiencies.map((def) => (
                      <div
                        key={def.id}
                        className="rounded-md p-2.5 bg-red-950/20 border border-red-500/20"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`
                            px-1.5 py-0.5 text-[9px] font-bold uppercase rounded
                            ${def.severity === 'critical'
                              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                              : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                            }
                          `}>
                            {def.severity}
                          </span>
                          <span className="text-xs font-semibold text-red-300">{def.title}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-mono mb-1">{def.regulation}</p>
                        <p className="text-[11px] text-slate-400 leading-relaxed">{def.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom gradient fade */}
      <div className="h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
    </div>
  );
}
