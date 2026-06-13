# EthicsBoard AI

**Multi-Agent Institutional Research Ethics Review System**
Band of Agents Hackathon · Track 3: Regulated & High-Stakes Workflows

---

## The Problem

Every hospital, university, and pharmaceutical company must submit research involving human subjects to an **Institutional Review Board (IRB)** before any study can begin. The IRB must review the protocol for ethics compliance, informed consent validity, risk-benefit justification, and data privacy — then a qualified human chair must approve the decision.

Today this process takes **6 to 12 weeks** of manual back-and-forth across email chains. A single missing clause in a consent form restarts the clock. Patient studies get delayed. There is no structured handoff, no traceability, and no coordination layer.

**EthicsBoard AI** puts four specialist agents into a Band room with the research protocol. Each reviews from their domain. Deficiencies surface in hours. The IRB chair makes the only decision they are legally allowed to make. The Band room is the audit record.

---

## Architecture

```
Researcher
    │
    ▼
Band Chat Room: "IRB Review — Protocol #IRB-PEDI-2026-0047"
    │
    ├── @ProtocolAgent     ← Google ADK + Gemini 2.5 Pro
    │       Parses protocol PDF, extracts structured fields,
    │       classifies risk level, initiates Band room workflow
    │
    ├── @EthicsAgent       ← Featherless AI (open-source reasoning)
    │       Reviews informed consent, Belmont Report principles,
    │       vulnerable population protections, assent requirements
    │
    ├── @PrivacyAgent      ← AI/ML API
    │       Checks HIPAA compliance, data sharing agreements,
    │       BAA requirements, retention policy, de-identification
    │
    └── @CommitteeAgent    ← FastAPI + Band HITL
            Aggregates findings, enforces mandatory human
            IRB chair approval, generates determination letter
```

All four agents communicate exclusively through Band's @mention routing. No agent has a direct API connection to another. The Band room conversation IS the legally required review record.

---

## How It Works

### Step 1 — Protocol Submission
```
Researcher: @ProtocolAgent Please review this research protocol.
            [uploads: IRB_Protocol_PEDI-2026-0047.pdf]
```

### Step 2 — Protocol Analysis (Google ADK + Gemini 2.5 Pro)
ProtocolAgent parses the PDF and extracts structured fields:
- Study type, population, intervention
- Risk classification (Minimal / Greater Than Minimal)
- Consent procedures described
- Data handling plan

```
ProtocolAgent: Protocol parsed.
               Study: Phase II RCT — MetaGlyX-400 in Pediatric T2DM
               Population: VULNERABLE (minors aged 8–16)
               Risk: GREATER THAN MINIMAL RISK → Full Board required
               @EthicsAgent please assess consent and risk-benefit.
```

### Step 3 — Ethics Review (Featherless AI)
EthicsAgent reviews against Belmont Report principles and 45 CFR 46:
- Respect for Persons: Is informed consent adequate for minors?
- Beneficence: Is the risk-benefit ratio justified?
- Justice: Is participant selection equitable?

```
EthicsAgent: Consent review: DEFICIENCIES FOUND
             1. Written assent form absent for participants aged 12–16.
                Required under 45 CFR 46.408 — minors capable of
                assent must provide written assent, not verbal only.
             2. Long-term hepatic monitoring requirement not disclosed
                in consent documents despite being listed in risk table.
             @PrivacyAgent please review data handling compliance.
```

### Step 4 — Privacy Review (AI/ML API)
PrivacyAgent checks data governance against HIPAA and institutional policy:
- De-identification method
- Third-party data sharing clauses
- Business Associate Agreement (BAA) requirements
- Data retention and destruction policy

```
PrivacyAgent: Data review: CONDITIONAL PASS WITH GAPS
              De-identification: Safe Harbour standard met.
              CRITICAL GAP: Data sharing with BioSync Research CRO
              governed by "confidentiality agreement" only.
              Under HIPAA 45 CFR 164.308(b)(1), a Business Associate
              Agreement is required before PHI transfer. BAA not
              referenced or appended to this submission.
              @CommitteeAgent: 2 ethics deficiencies + 1 privacy gap.
              Full Board review required. Human chair sign-off needed.
```

### Step 5 — Committee Coordination + HITL (FastAPI + Band)
CommitteeAgent aggregates all findings. It cannot issue a determination
to the researcher without human IRB chair approval — this is legally
mandated, not optional. CommitteeAgent dynamically adds the IRB chair
to the Band room using `add_participant_service`.

```
CommitteeAgent: [Adds @Dr.IRBChair to Band room]

                Dr. IRBChair — Full Board review required.

                FINDINGS SUMMARY:
                ├── Ethics: 2 deficiencies (assent form, hepatic
                │          disclosure missing from consent)
                └── Privacy: 1 gap (BAA for CRO data sharing absent)

                Protocol cannot proceed until deficiencies resolved.
                Please confirm decision: APPROVE / REQUEST REVISIONS
                / REJECT

Dr.IRBChair:    Request Revisions. Researcher must submit:
                (1) Written assent form for ages 12–16
                (2) Hepatic monitoring disclosure added to consent
                (3) Executed BAA with BioSync Research

CommitteeAgent: Decision recorded and timestamped.
                Generating official IRB determination letter.
                Complete review record preserved in Band room.
```

The entire Band room conversation — every agent's reasoning, every finding, every timestamp, the human decision — is the IRB review record. Regulators require exactly this.

---

## Technology Stack

| Component | Technology | Role |
|---|---|---|
| **Agent Coordination** | Band SDK | @mention routing, chat rooms, HITL, dynamic participant management, audit trail |
| **ProtocolAgent** | Google ADK + Gemini 2.5 Pro | PDF parsing, structured extraction, risk classification |
| **EthicsAgent** | Featherless AI | Open-source reasoning model for nuanced ethics review |
| **PrivacyAgent** | AI/ML API | Multi-model access for HIPAA and data governance checks |
| **CommitteeAgent** | FastAPI | Always-on coordination service, determination letter generation |
| **Document Processing** | PyPDF2 / pdfplumber | Protocol PDF parsing and text extraction |

### Why Cross-Framework

Band was built to coordinate agents across different frameworks and providers. EthicsBoard AI demonstrates this explicitly — four agents running on four different stacks, communicating only through Band's shared room. Remove Band and the workflow collapses entirely; there is no fallback coordination layer.

---

## Project Structure

```
ethicsboard-ai/
├── agents/
│   ├── protocol_agent/
│   │   ├── agent.py              # Google ADK + Gemini agent definition
│   │   ├── tools/
│   │   │   ├── pdf_parser.py     # Protocol PDF extraction
│   │   │   └── risk_classifier.py
│   │   └── agent_config.yaml
│   │
│   ├── ethics_agent/
│   │   ├── agent.py              # Featherless AI agent
│   │   ├── tools/
│   │   │   ├── consent_checker.py
│   │   │   └── belmont_reviewer.py
│   │   └── agent_config.yaml
│   │
│   ├── privacy_agent/
│   │   ├── agent.py              # AI/ML API agent
│   │   ├── tools/
│   │   │   ├── hipaa_checker.py
│   │   │   └── baa_validator.py
│   │   └── agent_config.yaml
│   │
│   └── committee_agent/
│       ├── main.py               # FastAPI service
│       ├── band_client.py        # Band SDK integration + HITL
│       ├── letter_generator.py   # Determination letter output
│       └── agent_config.yaml
│
├── demo/
│   ├── IRB_Protocol_PEDI-2026-0047.pdf   # Demo protocol (planted deficiencies)
│   └── sample_band_room_transcript.md    # Expected agent conversation
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ProtocolUpload.jsx
│   │   │   ├── BandRoomViewer.jsx     # Live Band room visualisation
│   │   │   └── DeterminationLetter.jsx
│   └── package.json
│
├── docker-compose.yml            # Run all four agents locally
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (frontend)
- uv package manager
- Band account at [band.ai](https://app.band.ai)
- API keys: Google AI Studio, Featherless AI, AI/ML API

### 1. Clone and configure

```bash
git clone https://github.com/Malikasadjaved/ethicsboard-ai
cd ethicsboard-ai
cp .env.example .env
```

Fill in `.env`:
```env
# Band credentials (one set per agent — see agent_config.yaml files)
BAND_PROTOCOL_AGENT_ID=<your-agent-uuid>
BAND_PROTOCOL_API_KEY=<your-agent-api-key>

BAND_ETHICS_AGENT_ID=<your-agent-uuid>
BAND_ETHICS_API_KEY=<your-agent-api-key>

BAND_PRIVACY_AGENT_ID=<your-agent-uuid>
BAND_PRIVACY_API_KEY=<your-agent-api-key>

BAND_COMMITTEE_AGENT_ID=<your-agent-uuid>
BAND_COMMITTEE_API_KEY=<your-agent-api-key>

# LLM providers
GOOGLE_API_KEY=<gemini-api-key>
FEATHERLESS_API_KEY=<featherless-api-key>
AIML_API_KEY=<aimlapi-key>
```

### 2. Register agents in Band

For each agent, go to [app.band.ai/agents](https://app.band.ai/agents):
- Click **New Agent** → **External Agent**
- Name it (e.g. `ProtocolAgent`)
- Copy the API key (shown only once) and Agent UUID into `.env`

### 3. Run all agents

```bash
docker compose up
```

Or run individually:
```bash
# Terminal 1
cd agents/protocol_agent && uv run python agent.py

# Terminal 2
cd agents/ethics_agent && uv run python agent.py

# Terminal 3
cd agents/privacy_agent && uv run python agent.py

# Terminal 4
cd agents/committee_agent && uv run uvicorn main:app --port 8000
```

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

---

## Running the Demo

1. Open the frontend at `localhost:5173`
2. Upload `demo/IRB_Protocol_PEDI-2026-0047.pdf`
3. Watch the Band room in real time as agents review the protocol
4. ProtocolAgent classifies: **Greater Than Minimal Risk** (pediatric population)
5. EthicsAgent finds: **missing written assent for ages 12–16** and **undisclosed hepatic monitoring**
6. PrivacyAgent finds: **missing BAA for CRO data sharing**
7. CommitteeAgent adds IRB chair to the room and requests human decision
8. IRB chair approves "Request Revisions" → determination letter generated
9. The complete Band room transcript serves as the regulatory review record

**What the demo proves:** Every handoff required Band. Every deficiency is real (planted deliberately in the protocol). The human decision is architecturally enforced. The audit trail is not a log — it is the document.

---

## The Deficiencies (Planted for Demo)

The demo protocol (`IRB_Protocol_PEDI-2026-0047.pdf`) contains three deliberate deficiencies for agents to catch:

| # | Location | Deficiency | Regulatory Basis |
|---|---|---|---|
| 1 | Section 5.2 | No written assent form for participants aged 12–16 | 45 CFR 46.408 |
| 2 | Section 5.2 | Long-term hepatic monitoring not disclosed in consent despite being in risk table | ICH E6(R2) 4.8.10 |
| 3 | Section 6.3 | CRO (BioSync Research) data sharing not covered by Business Associate Agreement | HIPAA 45 CFR 164.308(b)(1) |

These are real IRB deficiency categories — not invented for the demo.

---

## Hackathon Track

**Track 3: Regulated & High-Stakes Workflows**

EthicsBoard AI targets the first use case listed in Track 3: *"Healthcare coordination systems."* It satisfies all hackathon requirements:

- **3+ agents collaborating through Band** ✓ (4 agents)
- **Meaningful Band usage** ✓ (Band is the only coordination layer; all handoffs use @mention routing)
- **Real enterprise use case** ✓ ($4.2B IRB services market, legally mandated workflow)
- **Human-in-the-loop** ✓ (IRB chair approval is legally required, enforced by CommitteeAgent)
- **Cross-framework agents** ✓ (Google ADK, Featherless AI, AI/ML API, FastAPI — four different stacks)
- **Traceability** ✓ (Band room transcript = the regulatory record)

---

## Team

Built for the Band of Agents Hackathon · June 12–19, 2026

**Asad Javed** — Agent architecture, Google ADK, FastAPI, Band integration, demo narrative
Founder, Premium Logic · AI Engineer
[linkedin.com/in/malikasadjaved](https://linkedin.com/in/malikasadjaved) · [github.com/Malikasadjaved](https://github.com/Malikasadjaved)

---

## License

MIT License — see LICENSE for details.

---

*"A pediatric drug trial delayed by 10 weeks because an IRB reviewer missed a consent form clause. That is not a documentation problem — it is a coordination problem. EthicsBoard AI is the coordination layer."*
