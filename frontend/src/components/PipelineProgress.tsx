'use client';

import { useEffect, useState } from 'react';

type PipelineStage = 'pending' | 'protocol_review' | 'ethics_review' | 'privacy_review' | 'committee_review' | 'awaiting_chair' | 'completed';

interface PipelineProgressProps {
  currentStage: PipelineStage;
}

type NodeStatus = 'pending' | 'active' | 'complete';

interface NodeConfig {
  id: string;
  label: string;
  sublabel?: string;
  icon: string;
  activeColor: string;
  glowColor: string;
}

// The pipeline is NOT linear: after protocol analysis, ethics and privacy
// review IN PARALLEL; the committee then challenges ethics before the chair.
const protocolNode: NodeConfig = {
  id: 'protocol',
  label: 'Protocol Analysis',
  sublabel: 'risk-based routing',
  icon: '📋',
  activeColor: '#6366f1',
  glowColor: 'rgba(99, 102, 241, 0.3)',
};

const parallelNodes: NodeConfig[] = [
  {
    id: 'ethics',
    label: 'Ethics Review',
    icon: '⚖️',
    activeColor: '#a855f7',
    glowColor: 'rgba(168, 85, 247, 0.3)',
  },
  {
    id: 'privacy',
    label: 'Privacy Review',
    icon: '🔒',
    activeColor: '#06b6d4',
    glowColor: 'rgba(6, 182, 212, 0.3)',
  },
];

const challengeNode: NodeConfig = {
  id: 'challenge',
  label: 'Committee Challenge',
  sublabel: 'agent ⇄ agent',
  icon: '⚔️',
  activeColor: '#f59e0b',
  glowColor: 'rgba(245, 158, 11, 0.3)',
};

const chairNode: NodeConfig = {
  id: 'chair',
  label: 'Chair Decision',
  sublabel: 'human-in-the-loop',
  icon: '🏛️',
  activeColor: '#10b981',
  glowColor: 'rgba(16, 185, 129, 0.3)',
};

function getNodeStatus(nodeId: string, stage: PipelineStage): NodeStatus {
  if (stage === 'completed') return 'complete';
  if (stage === 'pending') return nodeId === 'protocol' ? 'active' : 'pending';

  switch (nodeId) {
    case 'protocol':
      return stage === 'protocol_review' ? 'active' : 'complete';
    case 'ethics':
      // active during the parallel phase AND the challenge (it defends its finding)
      if (stage === 'protocol_review') return 'pending';
      if (stage === 'ethics_review' || stage === 'privacy_review' || stage === 'committee_review') return 'active';
      return 'complete';
    case 'privacy':
      if (stage === 'protocol_review') return 'pending';
      if (stage === 'ethics_review' || stage === 'privacy_review') return 'active';
      return 'complete';
    case 'challenge':
      if (stage === 'committee_review') return 'active';
      if (stage === 'awaiting_chair') return 'complete';
      return 'pending';
    case 'chair':
      if (stage === 'awaiting_chair') return 'active';
      return 'pending';
    default:
      return 'pending';
  }
}

function NodeCircle({ node, status, size = 12 }: { node: NodeConfig; status: NodeStatus; size?: number }) {
  const px = size * 4; // tailwind w-12 = 48px when size=12
  return (
    <div className="relative" style={{ width: px, height: px }}>
      {status === 'active' && (
        <div
          className="absolute inset-[-4px] rounded-full animate-pulse"
          style={{ boxShadow: `0 0 20px ${node.glowColor}` }}
        />
      )}
      <div
        className={`
          rounded-full flex items-center justify-center border-2 transition-all duration-500
          ${status === 'complete'
            ? 'bg-emerald-500/20 border-emerald-500/50'
            : status === 'active'
              ? ''
              : 'bg-[#111128]/60 border-[#2a2a5a]/50'
          }
        `}
        style={{
          width: px,
          height: px,
          ...(status === 'active'
            ? { backgroundColor: `${node.activeColor}15`, borderColor: `${node.activeColor}60` }
            : {}),
        }}
      >
        {status === 'complete' ? (
          <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <span className={`${size >= 12 ? 'text-lg' : 'text-base'} ${status === 'pending' ? 'opacity-40 grayscale' : ''}`}>
            {node.icon}
          </span>
        )}
      </div>
      {status === 'active' && (
        <svg
          className="absolute inset-[-3px] animate-[spin_3s_linear_infinite]"
          style={{ width: px + 6, height: px + 6 }}
          viewBox="0 0 54 54"
        >
          <circle
            cx="27" cy="27" r="25" fill="none" strokeWidth="2"
            strokeDasharray="25 130" strokeLinecap="round"
            style={{ stroke: node.activeColor }}
          />
        </svg>
      )}
    </div>
  );
}

function NodeLabel({ node, status }: { node: NodeConfig; status: NodeStatus }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`
        text-[11px] font-semibold text-center leading-tight transition-colors duration-500
        ${status === 'complete' ? 'text-emerald-400' : status === 'active' ? 'text-white' : 'text-slate-600'}
      `}>
        {node.label}
      </span>
      {node.sublabel && (
        <span className={`text-[8px] font-mono uppercase tracking-wider ${
          status === 'pending' ? 'text-slate-700' : 'text-slate-500'
        }`}>
          {node.sublabel}
        </span>
      )}
      <span className={`
        text-[9px] font-mono uppercase tracking-wider transition-colors duration-500
        ${status === 'complete' ? 'text-emerald-500/60' : status === 'active' ? 'text-indigo-400/60' : 'text-slate-700'}
      `}>
        {status === 'complete' ? '✓ Done' : status === 'active' ? '● Active' : '○ Pending'}
      </span>
    </div>
  );
}

function Connector({ lit }: { lit: boolean }) {
  return (
    <div className="flex-1 flex items-center min-w-[16px]">
      <div className={`h-[2px] w-full transition-colors duration-700 ${lit ? 'bg-emerald-500/70' : 'bg-[#1e1e3a]'}`} />
    </div>
  );
}

export default function PipelineProgress({ currentStage }: PipelineProgressProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const sProtocol = getNodeStatus('protocol', currentStage);
  const sEthics = getNodeStatus('ethics', currentStage);
  const sPrivacy = getNodeStatus('privacy', currentStage);
  const sChallenge = getNodeStatus('challenge', currentStage);
  const sChair = getNodeStatus('chair', currentStage);

  const parallelStarted = sEthics !== 'pending' || sPrivacy !== 'pending';
  const parallelDone = sEthics === 'complete' && sPrivacy === 'complete';

  return (
    <div className="w-full rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <span className="text-base">🔄</span>
          <h2 className="text-sm font-bold text-white tracking-wide">Review Pipeline</h2>
          <span className="hidden sm:inline px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-widest rounded border border-purple-500/30 bg-purple-500/10 text-purple-400">
            non-linear · parallel + challenge
          </span>
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

      {/* Desktop: horizontal flow with parallel fork */}
      <div className={`hidden sm:flex items-center px-6 py-5 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
        {/* Protocol */}
        <div className="flex flex-col items-center gap-2 z-10">
          <NodeCircle node={protocolNode} status={sProtocol} />
          <NodeLabel node={protocolNode} status={sProtocol} />
        </div>

        <Connector lit={sProtocol === 'complete' && parallelStarted} />

        {/* Parallel fork: ethics ∥ privacy stacked */}
        <div className="relative flex flex-col items-center gap-3 z-10 px-2">
          <span className={`absolute -top-2 text-[8px] font-mono uppercase tracking-widest ${
            parallelStarted && !parallelDone ? 'text-purple-400' : 'text-slate-600'
          }`}>
            ∥ parallel
          </span>
          <div className="flex items-center gap-3 mt-2">
            <div className="flex flex-col items-center gap-1.5">
              <NodeCircle node={parallelNodes[0]} status={sEthics} size={10} />
              <NodeLabel node={parallelNodes[0]} status={sEthics} />
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <NodeCircle node={parallelNodes[1]} status={sPrivacy} size={10} />
              <NodeLabel node={parallelNodes[1]} status={sPrivacy} />
            </div>
          </div>
        </div>

        <Connector lit={parallelDone || sChallenge !== 'pending'} />

        {/* Committee challenge */}
        <div className="flex flex-col items-center gap-2 z-10">
          <NodeCircle node={challengeNode} status={sChallenge} />
          <NodeLabel node={challengeNode} status={sChallenge} />
        </div>

        <Connector lit={sChallenge === 'complete'} />

        {/* Chair HITL */}
        <div className="flex flex-col items-center gap-2 z-10">
          <NodeCircle node={chairNode} status={sChair} />
          <NodeLabel node={chairNode} status={sChair} />
        </div>
      </div>

      {/* Mobile: vertical list, parallel pair grouped */}
      <div className="flex sm:hidden flex-col gap-1 p-4">
        {/* Protocol */}
        <MobileRow node={protocolNode} status={sProtocol} />
        <MobileConnector lit={sProtocol === 'complete'} />

        {/* Parallel group */}
        <div className={`rounded-lg border p-2 ${
          parallelStarted && !parallelDone ? 'border-purple-500/30 bg-purple-500/5' : 'border-[#2a2a5a]/40'
        }`}>
          <p className="text-[8px] font-mono uppercase tracking-widest text-purple-400/80 mb-1 pl-1">∥ parallel reviews</p>
          <MobileRow node={parallelNodes[0]} status={sEthics} />
          <MobileRow node={parallelNodes[1]} status={sPrivacy} />
        </div>
        <MobileConnector lit={parallelDone} />

        <MobileRow node={challengeNode} status={sChallenge} />
        <MobileConnector lit={sChallenge === 'complete'} />

        <MobileRow node={chairNode} status={sChair} />
      </div>
    </div>
  );
}

function MobileRow({ node, status }: { node: NodeConfig; status: NodeStatus }) {
  return (
    <div
      className={`flex items-center gap-3 p-2.5 rounded-lg transition-all duration-500 ${status === 'active' ? 'bg-[#111128]/60' : ''}`}
      style={status === 'active' ? {
        boxShadow: `inset 0 0 20px ${node.glowColor}`,
        border: `1px solid ${node.activeColor}30`,
      } : {}}
    >
      <NodeCircle node={node} status={status} size={10} />
      <div className="flex-1">
        <p className={`text-xs font-bold transition-colors duration-500 ${
          status === 'complete' ? 'text-emerald-400' : status === 'active' ? 'text-white' : 'text-slate-600'
        }`}>
          {node.label}
          {node.sublabel && (
            <span className="ml-2 text-[8px] font-mono uppercase tracking-wider text-slate-500">{node.sublabel}</span>
          )}
        </p>
        <p className={`text-[9px] font-mono uppercase tracking-wider ${
          status === 'complete' ? 'text-emerald-500/60' : status === 'active' ? 'text-indigo-400/60' : 'text-slate-700'
        }`}>
          {status === 'complete' ? 'Completed' : status === 'active' ? 'In Progress' : 'Pending'}
        </p>
      </div>
      {status === 'active' && (
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: node.activeColor, animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: node.activeColor, animationDelay: '200ms' }} />
          <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ backgroundColor: node.activeColor, animationDelay: '400ms' }} />
        </div>
      )}
    </div>
  );
}

function MobileConnector({ lit }: { lit: boolean }) {
  return (
    <div className="flex justify-start pl-[22px]">
      <div className={`w-[2px] h-3 transition-colors duration-500 ${lit ? 'bg-emerald-500/40' : 'bg-[#1e1e3a]'}`} />
    </div>
  );
}
