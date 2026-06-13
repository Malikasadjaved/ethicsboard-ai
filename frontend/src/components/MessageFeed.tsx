'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

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

// Long messages (e.g. the full protocol text) collapse past this length
const TRUNCATE_AT = 420;

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
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [isAtBottom, setIsAtBottom] = useState(true);
  // Count of messages that arrived while the user was scrolled up
  const seenCountRef = useRef(0);
  const [unseenCount, setUnseenCount] = useState(0);

  const agentsPresent = useMemo(() => {
    const seen: string[] = [];
    messages.forEach((m) => {
      if (!seen.includes(m.agent)) seen.push(m.agent);
    });
    return seen;
  }, [messages]);

  const filteredMessages = useMemo(
    () => (agentFilter === 'all' ? messages : messages.filter((m) => m.agent === agentFilter)),
    [messages, agentFilter]
  );

  const scrollToBottom = useCallback((smooth = true) => {
    if (feedRef.current) {
      feedRef.current.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      });
    }
  }, []);

  const handleScroll = useCallback(() => {
    const el = feedRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    setIsAtBottom(atBottom);
    if (atBottom) {
      seenCountRef.current = messages.length;
      setUnseenCount(0);
    }
  }, [messages.length]);

  // Auto-scroll only when the user is already at the bottom — don't yank the
  // view away while they're reading earlier messages
  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom();
      seenCountRef.current = messages.length;
      setUnseenCount(0);
    } else {
      setUnseenCount(messages.length - seenCountRef.current);
    }
  }, [messages, isAtBottom, scrollToBottom]);

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

  const toggleExpanded = useCallback((id: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div className="relative flex flex-col h-full rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <h2 className="text-sm font-bold text-white tracking-wide">Band Room</h2>
          <span className="text-[10px] text-slate-500 font-mono">LIVE</span>
          <span className="hidden md:inline text-[9px] text-slate-600 font-mono uppercase tracking-wider pl-2 border-l border-[#2a2a5a]/60">
            audit ledger
          </span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {agentFilter === 'all'
            ? `${messages.length} messages`
            : `${filteredMessages.length} / ${messages.length} messages`}
        </span>
      </div>

      {/* Agent filter chips */}
      {agentsPresent.length > 1 && (
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-[#2a2a5a]/40 bg-[#0c0c22]/40 overflow-x-auto">
          <button
            onClick={() => setAgentFilter('all')}
            className={`
              flex-shrink-0 px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-all duration-200
              ${agentFilter === 'all'
                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                : 'bg-slate-800/40 text-slate-500 border-slate-700/40 hover:text-slate-300 hover:border-slate-600/60'
              }
            `}
          >
            All
          </button>
          {agentsPresent.map((agent) => {
            const color = agentColors[agent] || '#64748b';
            const active = agentFilter === agent;
            const count = messages.filter((m) => m.agent === agent).length;
            return (
              <button
                key={agent}
                onClick={() => setAgentFilter(active ? 'all' : agent)}
                className={`
                  flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold border transition-all duration-200
                  ${active ? '' : 'bg-slate-800/40 text-slate-500 border-slate-700/40 hover:text-slate-300 hover:border-slate-600/60'}
                `}
                style={active ? {
                  backgroundColor: `${color}1a`,
                  color,
                  borderColor: `${color}55`,
                } : undefined}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                {agent.replace('Agent', '')}
                <span className={`font-mono ${active ? 'opacity-70' : 'text-slate-600'}`}>{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Messages Container */}
      <div
        ref={feedRef}
        onScroll={handleScroll}
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

        {messages.length > 0 && filteredMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <p className="text-sm text-slate-500 font-medium">No messages from this agent yet</p>
            <button
              onClick={() => setAgentFilter('all')}
              className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Show all messages
            </button>
          </div>
        )}

        {filteredMessages.map((msg, index) => {
          const color = agentColors[msg.agent] || '#64748b';
          const agentIcon = agentIcons[msg.agent] || '🤖';
          const borderType = getMessageBorderType(msg.content, msg.message_type);
          const challengeKind = getChallengeKind(msg.content);
          const isVisible = visibleMessages.has(msg.id);
          const isLong = msg.content.length > TRUNCATE_AT;
          const isExpanded = expandedMessages.has(msg.id);
          const displayContent = isLong && !isExpanded
            ? `${msg.content.slice(0, TRUNCATE_AT).trimEnd()}…`
            : msg.content;

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
                  <span className="ml-auto text-[10px] text-slate-600 font-mono opacity-40 group-hover:opacity-100 transition-opacity">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>

                {/* Message Content */}
                <div className="text-[13px] text-slate-300 leading-relaxed pl-9 whitespace-pre-wrap break-words">
                  {highlightContent(displayContent)}
                </div>

                {/* Expand / collapse for long messages */}
                {isLong && (
                  <div className="pl-9 mt-1.5">
                    <button
                      onClick={() => toggleExpanded(msg.id)}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      {isExpanded ? 'Show less' : `Show full message (${(msg.content.length / 1000).toFixed(1)}k chars)`}
                      <svg
                        className={`w-3 h-3 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                      </svg>
                    </button>
                  </div>
                )}

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

      {/* Jump-to-latest pill — appears when scrolled up and new messages arrive */}
      {!isAtBottom && (
        <button
          onClick={() => scrollToBottom()}
          className="
            absolute bottom-6 left-1/2 -translate-x-1/2 z-10
            flex items-center gap-1.5 px-3 py-1.5 rounded-full
            bg-indigo-600/90 hover:bg-indigo-500/90 backdrop-blur-md
            border border-indigo-400/40 shadow-lg shadow-indigo-500/30
            text-[11px] font-semibold text-white
            transition-all duration-300 animate-fade-in-up
          "
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
          </svg>
          {unseenCount > 0 ? `${unseenCount} new message${unseenCount === 1 ? '' : 's'}` : 'Jump to latest'}
        </button>
      )}

      {/* Bottom gradient fade */}
      <div className="h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
    </div>
  );
}
