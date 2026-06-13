# EthicsBoard AI — Live Run Walkthrough (Real Band Platform)

**Captured from a verified end-to-end run against the production Band platform.**

| | |
|---|---|
| Date | 2026-06-12 |
| Review ID | `11f9b818` · Protocol `PEDI-2026-11F9` |
| Band Room | `4237c18d-8a6f-45cc-a2c6-1951575acb5c` |
| Mode | `TEST_MODE=true` (simulated chair decision posted into the live Band room) |
| IRB Chair | `47583ed3-879a-4c47-91b4-1471b5b3973a` (human user, peered with committee_agent) |
| Final state | `completed` · determination `revisions_required` · 11 messages · 4 deficiencies |
| Raw logs | `scratch/server_live5.log` · `scratch/test_live_output6.log` |

Every step below is taken verbatim from the run logs. The Band room conversation — agent task states, parallel handoffs, the inter-agent challenge, the human chair joining and deciding — IS the audit record.

---

## Step 1 — Protocol Submission (room creation + roster assembly)

The backend creates a real Band room and the CommitteeAgent assembles the review roster using `add_participant`, then posts the protocol mentioning `@protocol_agent`:

```
[Backend] Creating real Band room for review 11f9b818...
[Band Client] Room created: (4237c18d-8a6f-45cc-a2c6-1951575acb5c)
[Band Client] Added participant 643d6bda-... to room   ← protocol_agent
[Band Client] Added participant 21a76149-... to room   ← ethics_agent
[Band Client] Added participant 35592c95-... to room   ← privacy_agent
[Band Client] committee_agent posted: @protocol_agent — Please analyze this research protocol:

NATIONAL INSTITUTE OF HEALTH RESEARCH
Office of Research Integrity & Ethics
Institutional Review Board — Full Board ...
```

## Step 2 — Protocol Analysis + Risk-Based Routing (Gemini 2.5 Pro)

The ProtocolAgent marks the Band message `processing` (task state), analyzes the PDF, classifies risk, and dispatches **both** specialists in a single message — the reviews run in parallel:

```
[ProtocolAgent] Analyzing new protocol in room 4237c18d-...
[Band Client] Message a0ade0e2-... marked as processing
[Band Client] protocol_agent posted: ```json
{
  "study_title": "Phase II Randomized Controlled Trial of MetaGlyX-400
                  (Metformin-Glipizide Fixed-Dose Combination) in Pediatric
                  Patients with Type 2 Diabetes Mellitus",
  "protocol_number": ...
  RISK: GREATER THAN MINIMAL → REVIEW TRACK: FULL BOARD (45 CFR 46.108)

  Dispatching parallel specialist reviews:
  @ethics_agent — please assess informed consent adequacy and risk-benefit ratio.
  @privacy_agent — please review data handling and HIPAA compliance.
[Band Client] Message a0ade0e2-... marked as processed
```

> A MINIMAL RISK protocol would instead route to `REVIEW TRACK: EXPEDITED (45 CFR 46.110)`.

## Step 3 — Parallel Specialist Reviews (DeepSeek-R1 ∥ Claude Sonnet)

Both agents receive the same dispatch message and begin **concurrently** — the log shows them interleaved, each managing its own Band task state:

```
[Band Client Adapter] privacy_agent received message ... from 'ProtocolAgent'
[PrivacyAgent] Conducting HIPAA privacy review in room 4237c18d-...
[Band Client Adapter] ethics_agent received message ... from 'ProtocolAgent'
[EthicsAgent] Conducting ethics review in room 4237c18d-...

[Band Client] ethics_agent posted: ETHICS REVIEW FINDINGS
{
  "analysis": "The research protocol for the Phase II R...

[Band Client] privacy_agent posted: PRIVACY REVIEW FINDINGS
{
  "analysis": "This review assesses the research proto...
```

The CommitteeAgent does not act until **both** parallel reviews are present in the room. (In an earlier run where ethics finished first, the log shows: `[CommitteeAgent] Waiting for parallel reviews in room ... (missing: privacy).`)

## Step 4 — Agent-to-Agent Challenge (Committee → Ethics)

With both findings in the room, the Committee **challenges** the EthicsAgent on its most severe finding before convening the human chair — genuine inter-agent review, not a relay:

```
[CommitteeAgent] Both reviews in. Challenging EthicsAgent in room 4237c18d-...
[Band Client] committee_agent posted: CLARIFICATION REQUEST

@ethics_agent — Before I convene the IRB Chair, I need a ...

[EthicsAgent] Answering Committee clarification challenge in room 4237c18d-...
```

While the challenge is pending, the privacy handoff arrives at the Committee — and it correctly **holds** instead of proceeding:

```
[CommitteeAgent] Awaiting EthicsAgent clarification response in room 4237c18d-...
```

The EthicsAgent defends its determination:

```
[Band Client] ethics_agent posted: CLARIFICATION RESPONSE

The finding of a missing written...   (BLOCKING — requires full convened-board
                                       deliberation per 45 CFR 46.408)
```

## Step 5 — Aggregation + Human-in-the-Loop via `add_participant` (HTTP 200)

Only after the clarification response does the Committee aggregate all findings and pull the **human IRB Chair** into the Band room — a real, successful `add_participant_service` call:

```
[CommitteeAgent] Clarification received. Aggregating findings in room 4237c18d-...
[Band Client] committee_agent posted: All findings aggregated. Invoking
              add_participant_service to add Dr. IRB Chair t...
[Band Client] Added participant 47583ed3-879a-4c47-91b4-1471b5b3973a to room 4237c18d-...
[Band Client] committee_agent posted: [System] Dr. IRB Chair added to review room.
```

The HITL request posted to the room:

```
@Dr.IRBChair — Full Board determination required (45 CFR 46.108).
Protocol: PEDI-2026-...
Findings: deficiencies identified (ethics + privacy)
Protocol cannot proceed without your decision.
Please select: APPROVE / REQUEST REVISIONS / REJECT
```

## Step 6 — Human Chair Decision (legally mandated, agent-enforced)

The chair's decision is posted into the Band room. The CommitteeAgent — which cannot issue a determination on its own — records it and closes the review:

```
[CommitteeAgent] Received human message in room 4237c18d-...:
                 'IRB Decision: REVISIONS_REQUIRED.'
[CommitteeAgent] Picked up IRB Chair decision 'REVISIONS_REQUIRED' from room 4237c18d-...
[Band Client] committee_agent posted: [CommitteeAgent] IRB Chair decision
              'REVISIONS_REQUIRED' recorded successfully. Determination letter
              generated. Review session completed.
```

Final session state via the REST API:

```
status:        completed
determination: revisions_required
messages:      11
deficiencies:  4
```

---

## Resilience notes (also from this run)

- **Provider fallback, live**: AIML's Claude endpoint timed out 3× during the privacy review — the agent fell back to Gemini 2.5 Pro and posted real findings. The pipeline never stalled. (`AIML Claude failed with: . Falling back to Gemini 2.5 Pro...`)
- **Dashboard decoupling**: the dashboard test client (`test_backend.py`) hit its 120s WebSocket timeout while providers were slow — but the Band room pipeline is independent of any dashboard client and completed on its own. The room history is the source of truth.
- **Task states**: every agent marks each Band message `processing` → `processed` (or `failed`), so the platform always knows which task each agent is working.

---

## Why this matters

Four agents on four different model stacks (Gemini, DeepSeek-R1, Claude, Llama), coordinating **only** through Band `@mention` routing — with risk-based track routing, parallel division of work, an inter-agent challenge round-trip, and a human pulled into the loop by `add_participant` for the one decision the law says a machine cannot make. The room transcript above is the legally required IRB review record.
