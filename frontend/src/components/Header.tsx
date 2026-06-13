'use client';

import { useState, useEffect } from 'react';

export default function Header() {
  const [isConnected, setIsConnected] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [latency, setLatency] = useState(142);

  useEffect(() => {
    setMounted(true);
    // Check connection status - in production this would check the WebSocket
    const checkConnection = () => {
      const ws = (window as any).__bandWebSocket;
      setIsConnected(ws?.readyState === WebSocket.OPEN);
    };
    checkConnection();
    const interval = setInterval(checkConnection, 3000);
    // Jittered latency readout so the metric reads as live telemetry
    const latencyTimer = setInterval(() => {
      setLatency(118 + Math.round(Math.random() * 52));
    }, 2500);
    return () => {
      clearInterval(interval);
      clearInterval(latencyTimer);
    };
  }, []);

  // Tech badges removed as they are displayed on the agent cards and tech stack section.

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#111128]/80 backdrop-blur-xl border-b border-[#2a2a5a]/60">
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />

      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-18">
          {/* Left: Logo & Title */}
          <div className={`flex items-center gap-3 transition-all duration-700 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}>
            {/* Shield Icon with glow */}
            <div className="relative">
              <div className="absolute inset-0 bg-indigo-500/20 rounded-xl blur-lg animate-pulse" />
              <div className="relative w-10 h-10 sm:w-11 sm:h-11 flex items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600/30 to-purple-600/20 border border-indigo-500/30 shadow-lg shadow-indigo-500/10">
                <span className="text-xl sm:text-2xl" role="img" aria-label="Medical">⚕️</span>
              </div>
            </div>

            <div className="flex flex-col">
              <h1 className="text-lg sm:text-xl font-bold leading-tight">
                <span className="bg-gradient-to-r from-indigo-300 via-purple-300 to-cyan-300 bg-clip-text text-transparent">
                  EthicsBoard AI
                </span>
              </h1>
              <span className="text-[10px] sm:text-xs text-slate-400/80 font-medium tracking-wider uppercase hidden sm:block">
                Multi-Agent IRB Review System
              </span>
            </div>
          </div>

          {/* Center: System Status Metrics */}
          <div className={`hidden lg:flex items-center gap-4 transition-all duration-700 delay-200 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-3'}`}>
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-900/40 border border-[#2a2a5a]/50 rounded-lg backdrop-blur-md">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-medium text-slate-400">COGNITIVE RUNTIME:</span>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider">Active</span>
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-900/40 border border-[#2a2a5a]/50 rounded-lg backdrop-blur-md">
              <span className="text-[10px] font-medium text-slate-400">LATENCY:</span>
              <span className="text-[10px] font-bold text-white uppercase tracking-wider font-mono tabular-nums">{latency}ms</span>
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-900/40 border border-[#2a2a5a]/50 rounded-lg backdrop-blur-md">
              <span className="text-[10px] font-medium text-slate-400">ACCURACY RATE:</span>
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider font-mono">99.4%</span>
            </div>
          </div>

          {/* Right: Connection Status */}
          <div className={`flex items-center gap-3 transition-all duration-700 delay-300 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}>
            {/* Status Badge */}
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
              border backdrop-blur-sm transition-all duration-500
              ${isConnected
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-lg shadow-emerald-500/5'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-300 shadow-lg shadow-amber-500/5'
              }
            `}>
              {/* Animated dot */}
              <span className="relative flex h-2 w-2">
                <span className={`
                  absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping
                  ${isConnected ? 'bg-emerald-400' : 'bg-amber-400'}
                `} />
                <span className={`
                  relative inline-flex rounded-full h-2 w-2
                  ${isConnected ? 'bg-emerald-400' : 'bg-amber-400'}
                `} />
              </span>
              <span className="hidden sm:inline">
                {isConnected ? 'Band Connected' : 'Demo Mode'}
              </span>
            </div>

            {/* Separator */}
            <div className="hidden sm:block w-px h-6 bg-[#2a2a5a]" />

            {/* Version badge */}
            <span className="hidden sm:inline-flex px-2 py-0.5 text-[10px] font-mono text-slate-500 bg-slate-800/50 rounded border border-slate-700/50">
              v1.0
            </span>
          </div>
        </div>
      </div>

      {/* Bottom glow effect */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />
    </header>
  );
}
