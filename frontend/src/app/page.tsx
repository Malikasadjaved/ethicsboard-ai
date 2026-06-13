"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Header from "@/components/Header";
import AgentCard from "@/components/AgentCard";
import MessageFeed from "@/components/MessageFeed";
import DeficiencyPanel from "@/components/DeficiencyPanel";
import DecisionPanel from "@/components/DecisionPanel";
import UploadPanel from "@/components/UploadPanel";
import PipelineProgress from "@/components/PipelineProgress";

// --- Types ---

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
  metadata?: Record<string, unknown>;
}

type ReviewStatus =
  | "idle"
  | "pending"
  | "protocol_review"
  | "ethics_review"
  | "privacy_review"
  | "committee_review"
  | "awaiting_chair"
  | "completed";

type AgentStatus = "idle" | "active" | "complete" | "error";

// --- Agent Config ---

const AGENTS = [
  {
    name: "ProtocolAgent",
    framework: "LangGraph",
    model: "Gemini 2.5 Pro",
    provider: "AI/ML API",
    icon: "protocol",
    color: "#6366f1",
  },
  {
    name: "EthicsAgent",
    framework: "Pydantic AI",
    model: "DeepSeek-R1",
    provider: "Featherless AI",
    icon: "ethics",
    color: "#a855f7",
  },
  {
    name: "PrivacyAgent",
    framework: "CrewAI",
    model: "Claude Sonnet",
    provider: "AI/ML API",
    icon: "privacy",
    color: "#06b6d4",
  },
  {
    name: "CommitteeAgent",
    framework: "FastAPI",
    model: "Llama 3.1 70B",
    provider: "Featherless AI",
    icon: "committee",
    color: "#f59e0b",
  },
];

// --- API URL ---
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8008";

export default function Dashboard() {
  const [status, setStatus] = useState<ReviewStatus>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [deficiencies, setDeficiencies] = useState<Deficiency[]>([]);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [protocolNumber, setProtocolNumber] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [determination, setDetermination] = useState<string | null>(null);
  const [reviewTrack, setReviewTrack] = useState<"expedited" | "full_board" | null>(null);
  const [escalated, setEscalated] = useState(false);
  const [bandRoomId, setBandRoomId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // --- Derive agent statuses from review status ---
  // Ethics and Privacy review IN PARALLEL after the protocol dispatch; during
  // the committee challenge phase Ethics goes active again (it is defending
  // its finding), while the Committee coordinates.
  const getAgentStatus = useCallback(
    (agentName: string): AgentStatus => {
      const statusMap: Record<ReviewStatus, Record<string, AgentStatus>> = {
        idle: {},
        pending: { ProtocolAgent: "active" },
        protocol_review: {
          ProtocolAgent: "active",
        },
        ethics_review: {
          // Parallel phase: both specialists work simultaneously
          ProtocolAgent: "complete",
          EthicsAgent: "active",
          PrivacyAgent: "active",
        },
        privacy_review: {
          // Still the parallel phase — one review has landed, both shown active
          // until the Committee confirms it has both
          ProtocolAgent: "complete",
          EthicsAgent: "active",
          PrivacyAgent: "active",
        },
        committee_review: {
          // Challenge phase: Committee questions Ethics, which must respond
          ProtocolAgent: "complete",
          EthicsAgent: "active",
          PrivacyAgent: "complete",
          CommitteeAgent: "active",
        },
        awaiting_chair: {
          ProtocolAgent: "complete",
          EthicsAgent: "complete",
          PrivacyAgent: "complete",
          CommitteeAgent: "active",
        },
        completed: {
          ProtocolAgent: "complete",
          EthicsAgent: "complete",
          PrivacyAgent: "complete",
          CommitteeAgent: "complete",
        },
      };
      return statusMap[status]?.[agentName] || "idle";
    },
    [status]
  );

  // --- WebSocket connection ---
  useEffect(() => {
    if (!reviewId) return;

    const ws = new WebSocket(`${API_URL.replace("http", "ws")}/ws/review/${reviewId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "message") {
        const msg: Message = data.data;
        setMessages((prev) => [...prev, msg]);

        // Collect deficiencies
        if (msg.deficiencies && msg.deficiencies.length > 0) {
          setDeficiencies((prev) => [...prev, ...msg.deficiencies!]);
        }

        // Derive the review track from the ProtocolAgent's routing decision
        if (msg.content.includes("REVIEW TRACK: EXPEDITED")) {
          setReviewTrack("expedited");
        } else if (msg.content.includes("REVIEW TRACK: FULL BOARD")) {
          setReviewTrack("full_board");
        }
        // Expedited reviews escalate to full board when deficiencies surface
        if (msg.content.includes("ESCALATION:")) {
          setEscalated(true);
          setReviewTrack("full_board");
        }
      }

      if (data.type === "status_update") {
        setStatus(data.data.status as ReviewStatus);
        if (data.data.determination) {
          setDetermination(data.data.determination);
        }
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      ws.close();
    };
  }, [reviewId]);

  // --- Fetch the real Band room ID (created asynchronously after upload) ---
  useEffect(() => {
    if (!reviewId || bandRoomId) return;
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/review/${reviewId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.band_room_id) {
            setBandRoomId(data.band_room_id);
            clearInterval(timer);
          }
        }
      } catch {
        // backend not ready yet — keep polling
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [reviewId, bandRoomId]);

  // --- Upload handler ---
  const handleUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setMessages([]);
      setDeficiencies([]);
      setDetermination(null);
      setReviewTrack(null);
      setEscalated(false);
      setBandRoomId(null);
      setStatus("pending");

      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`${API_URL}/api/review/start`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();
        setReviewId(data.review_id);
        setProtocolNumber(data.protocol_number);
      } catch (err) {
        console.error("Upload error:", err);
        setStatus("idle");
      } finally {
        setIsUploading(false);
      }
    },
    []
  );

  // --- Decision handler ---
  const handleDecision = useCallback(
    async (decision: string) => {
      if (!reviewId) return;

      try {
        await fetch(`${API_URL}/api/review/${reviewId}/decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision }),
        });
      } catch (err) {
        console.error("Decision error:", err);
      }
    },
    [reviewId]
  );

  // --- Render ---
  return (
    <div className="min-h-screen bg-[#02020d] text-slate-100 relative overflow-hidden">
      {/* Blurred radial glow effects for background depth */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] rounded-full bg-indigo-500/5 blur-[120px] pointer-events-none -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-[150px] pointer-events-none translate-x-1/3 translate-y-1/3" />

      <Header />

      {/* Main Content */}
      <main className="pt-20 px-4 lg:px-8 pb-8 max-w-[1600px] mx-auto">
        {/* Pipeline Progress */}
        {status !== "idle" && (
          <div className="mb-6 animate-fade-in-up">
            <PipelineProgress currentStage={status} />
          </div>
        )}

        {/* Agent Cards Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {AGENTS.map((agent, i) => (
            <div
              key={agent.name}
              className="animate-fade-in-up"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <AgentCard
                {...agent}
                status={getAgentStatus(agent.name)}
              />
            </div>
          ))}
        </div>

        {/* Main Grid: Upload/Messages + Deficiencies */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Upload + Message Feed */}
          <div className="lg:col-span-2 space-y-6">
            {/* Upload Panel (shown when idle or can be minimized) */}
            {status === "idle" && (
              <div className="animate-fade-in-up">
                <UploadPanel onUpload={handleUpload} isUploading={isUploading} />
              </div>
            )}

            {/* Protocol Info Bar (shown during review) */}
            {status !== "idle" && protocolNumber && (
              <div className="glass rounded-xl p-4 flex items-center justify-between animate-fade-in-up">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-brand-500/20 flex items-center justify-center">
                    <span className="text-lg">📋</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Protocol {protocolNumber}
                    </h3>
                    <p className="text-xs text-gray-400">
                      IRB Review in Progress
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* Risk-based review track badge */}
                  {reviewTrack && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                        escalated
                          ? "bg-red-500/15 text-red-400 border-red-500/30"
                          : reviewTrack === "expedited"
                          ? "bg-cyan-500/15 text-cyan-400 border-cyan-500/30"
                          : "bg-indigo-500/15 text-indigo-400 border-indigo-500/30"
                      }`}
                      title={
                        escalated
                          ? "Expedited review terminated per 45 CFR 46.110(b) — deficiencies found"
                          : reviewTrack === "expedited"
                          ? "Minimal risk — designated-reviewer sign-off (45 CFR 46.110)"
                          : "Greater than minimal risk — convened board required (45 CFR 46.108)"
                      }
                    >
                      {escalated
                        ? "⚠ Escalated to Full Board"
                        : reviewTrack === "expedited"
                        ? "⚡ Expedited Track"
                        : "🏛 Full Board Track"}
                    </span>
                  )}
                  {determination && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        determination === "approved"
                          ? "bg-green-500/20 text-green-400"
                          : determination === "rejected"
                          ? "bg-red-500/20 text-red-400"
                          : "bg-amber-500/20 text-amber-400"
                      }`}
                    >
                      {determination === "revisions_required"
                        ? "Revisions Required"
                        : determination.charAt(0).toUpperCase() +
                          determination.slice(1)}
                    </span>
                  )}
                  <span className="text-xs text-gray-500 font-mono" title={bandRoomId || undefined}>
                    {bandRoomId
                      ? `Band Room: ${bandRoomId.slice(0, 8)}…`
                      : "Band Room: connecting…"}
                  </span>
                </div>
              </div>
            )}

            {/* Message Feed */}
            {status !== "idle" && (
              <div className="animate-fade-in-up" style={{ animationDelay: "200ms" }}>
                <div className="glass rounded-xl overflow-hidden">
                  <div className="px-5 py-3 border-b border-[#2a2a5a] flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                      Band Room — Live Review Feed
                    </h2>
                    <span className="text-xs text-gray-500">
                      {messages.length} messages
                    </span>
                  </div>
                  <div className="h-[500px]">
                    <MessageFeed messages={messages} />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Deficiencies + Decision */}
          <div className="space-y-6">
            {/* Deficiency Panel */}
            {status !== "idle" && (
              <div className="animate-slide-in-right">
                <DeficiencyPanel deficiencies={deficiencies} />
              </div>
            )}

            {/* HITL Decision Panel */}
            <DecisionPanel
              visible={status === "awaiting_chair"}
              onDecision={handleDecision}
              protocolNumber={protocolNumber}
            />

            {/* Welcome Card (idle state) */}
            {status === "idle" && (
              <div className="glass rounded-xl p-6 animate-fade-in-up" style={{ animationDelay: "300ms" }}>
                <h2 className="text-lg font-bold gradient-text mb-3">
                  How It Works
                </h2>
                <div className="space-y-4">
                  {[
                    {
                      step: "1",
                      title: "Upload Protocol",
                      desc: "Submit a research protocol PDF for review",
                    },
                    {
                      step: "2",
                      title: "Agent Analysis",
                      desc: "4 specialist agents review through Band",
                    },
                    {
                      step: "3",
                      title: "Deficiency Detection",
                      desc: "Regulatory gaps identified with citations",
                    },
                    {
                      step: "4",
                      title: "Human Decision",
                      desc: "IRB Chair approves, revises, or rejects",
                    },
                  ].map((item) => (
                    <div key={item.step} className="flex gap-3">
                      <div className="w-8 h-8 rounded-lg bg-brand-500/20 flex items-center justify-center shrink-0">
                        <span className="text-sm font-bold text-brand-400">
                          {item.step}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-white">
                          {item.title}
                        </h3>
                        <p className="text-xs text-gray-400">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tech Stack Card */}
            {status === "idle" && (
              <div className="glass rounded-xl p-6 animate-fade-in-up" style={{ animationDelay: "400ms" }}>
                <h2 className="text-lg font-bold text-white mb-3">
                  Tech Stack
                </h2>
                <div className="space-y-3">
                  {[
                    { name: "Band", desc: "Agent collaboration layer", color: "bg-indigo-500" },
                    { name: "AI/ML API", desc: "Gemini + Claude models", color: "bg-purple-500" },
                    { name: "Featherless AI", desc: "DeepSeek + Llama models", color: "bg-cyan-500" },
                    { name: "4 Frameworks", desc: "LangGraph, Pydantic AI, CrewAI, FastAPI", color: "bg-amber-500" },
                  ].map((tech) => (
                    <div key={tech.name} className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${tech.color}`} />
                      <div>
                        <span className="text-sm font-medium text-white">{tech.name}</span>
                        <span className="text-xs text-gray-400 ml-2">{tech.desc}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
