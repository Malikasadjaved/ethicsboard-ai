"""CommitteeAgent — IRB Committee Coordinator & HITL Enforcer

Framework: FastAPI (direct integration)
Model: Llama 3.1 70B via Featherless AI
Role: Aggregates findings from all specialist agents, enforces mandatory
      human IRB chair approval, and generates determination letters.
"""

import os
import re
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Featherless AI client (OpenAI-compatible)
featherless_client = AsyncOpenAI(
    api_key=os.getenv("FEATHERLESS_API_KEY"),
    base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
)

from agents.llm_utils import call_llm_with_retry

# NousResearch mirror — identical Llama 3.1 70B weights; meta-llama/ repo is
# gated on Featherless (requires HuggingFace OAuth) and returns 403
COMMITTEE_MODEL = "NousResearch/Meta-Llama-3.1-70B-Instruct"

# --- Determination Letter Prompt ---

DETERMINATION_PROMPT = """You are an IRB Committee Coordinator generating an official IRB Determination Letter. Based on the complete review record and the IRB Chair's decision, generate a formal determination letter.

Review Record:
{review_record}

IRB Chair Decision: {decision}
IRB Chair Comments: {chair_comments}

Generate a formal IRB Determination Letter with the following sections:
1. HEADER: Protocol number, date, PI name, study title
2. DETERMINATION: The chair's decision (Approved / Revisions Required / Not Approved)
3. FINDINGS SUMMARY: List all deficiencies identified by the review
4. REQUIRED ACTIONS: What the PI must do to address each deficiency (if revisions required)
5. RESUBMISSION INSTRUCTIONS: Timeline and process for resubmission (if applicable)
6. REGULATORY BASIS: Cite the specific regulations that apply
7. FOOTER: Signature block for IRB Chair

Format as a professional, formal letter suitable for regulatory filing."""


def _parse_json_deficiencies(msg: str) -> Optional[List[dict]]:
    """Extract the structured deficiencies array from an agent's JSON findings block."""
    match = re.search(r"\{.*\}", msg, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict) and isinstance(data.get("deficiencies"), list):
            return [d for d in data["deficiencies"] if isinstance(d, dict)]
    except Exception:
        pass
    return None


def extract_review_track(room_messages: List[str]) -> str:
    """Read the review track chosen by ProtocolAgent's risk classification."""
    for msg in room_messages:
        if "REVIEW TRACK: EXPEDITED" in msg:
            return "EXPEDITED"
        if "REVIEW TRACK: FULL BOARD" in msg:
            return "FULL_BOARD"
    return "FULL_BOARD"


async def aggregate_findings(room_messages: List[str]) -> Dict:
    """Aggregate all agent findings from Band room history."""
    deficiencies = []
    passes = []
    seen = set()

    for msg in room_messages:
        # Parse structured JSON findings (ethics/privacy agents post JSON blocks)
        structured = _parse_json_deficiencies(msg)
        if structured:
            for d in structured:
                line = f"DEFICIENCY {d.get('id', '?')}: {d.get('title', 'Compliance Issue')} — {d.get('regulation', 'Unknown Regulation')} [{d.get('severity', 'major')}]"
                if line not in seen:
                    seen.add(line)
                    deficiencies.append(line)
            continue
        # Parse legacy line-format deficiencies
        if "DEFICIENCY" in msg:
            lines = msg.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("DEFICIENCY") and stripped not in seen:
                    seen.add(stripped)
                    deficiencies.append(stripped)
        # Parse passes
        if "PASS:" in msg:
            lines = msg.split("\n")
            for line in lines:
                if line.strip().startswith("PASS:"):
                    passes.append(line.strip())

    return {
        "deficiencies": deficiencies,
        "passes": passes,
        "total_deficiencies": len(deficiencies),
        "requires_full_board": len(deficiencies) > 0,
    }


async def generate_determination_letter(
    review_record: str,
    decision: str,
    chair_comments: str = ""
) -> str:
    """Generate formal IRB determination letter using Llama 3.1 with retries."""
    try:
        response = await call_llm_with_retry(
            client=featherless_client,
            model=COMMITTEE_MODEL,
            messages=[
                {"role": "system", "content": "You are an IRB Committee Coordinator. Generate formal, regulatory-compliant determination letters."},
                {"role": "user", "content": DETERMINATION_PROMPT.format(
                    review_record=review_record,
                    decision=decision,
                    chair_comments=chair_comments
                )}
            ],
            temperature=0.3,
            max_tokens=3000,
            timeout=120.0,  # Featherless serverless cold start can take ~60s
            max_retries=3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Determination letter generation failed: {str(e)}. Manual generation required."


def format_clarification_request(findings: Dict) -> str:
    """Format the agent-to-agent clarification challenge for EthicsAgent.

    Before summoning the human chair, the Committee challenges the Ethics
    specialist on whether its most severe finding can be resolved with minor
    revisions (which would keep an expedited track viable) or blocks approval.
    """
    top_finding = findings["deficiencies"][0] if findings["deficiencies"] else "No deficiencies recorded"
    return f"""CLARIFICATION REQUEST

@ethics_agent — Before I convene the IRB Chair, I need a determination from you:

Your most severe finding: {top_finding}

Question: Does this finding constitute a blocking deficiency that requires
full convened-board deliberation, or can it be resolved through minor protocol
revisions under expedited handling (45 CFR 46.110(b)(2))?

Please respond with CLARIFICATION RESPONSE and your reasoning."""


async def format_hitl_request(findings: Dict, protocol_number: str, review_track: str = "FULL_BOARD") -> str:
    """Format the HITL request message for the Band room, routed by review track."""
    deficiency_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(findings["deficiencies"]))

    if review_track == "EXPEDITED" and findings["total_deficiencies"] == 0:
        header = """@Dr.IRBChair — EXPEDITED determination requested (45 CFR 46.110).
This protocol was classified MINIMAL RISK and no deficiencies were found.
A single designated-reviewer sign-off is sufficient; no convened board required."""
    elif review_track == "EXPEDITED":
        header = f"""ESCALATION: Expedited review terminated per 45 CFR 46.110(b).
Protocol was classified MINIMAL RISK, but {findings['total_deficiencies']} deficiencies were identified during specialist review. Escalating to FULL BOARD review.

@Dr.IRBChair — Full Board determination required."""
    else:
        header = "@Dr.IRBChair — Full Board determination required (45 CFR 46.108)."

    return f"""All findings aggregated. Invoking add_participant_service to add Dr. IRB Chair to this Band room...

{header}
Protocol: {protocol_number}
Findings: {findings['total_deficiencies']} deficiencies identified:
{deficiency_list}

Protocol cannot proceed without your decision.

Please select: APPROVE / REQUEST REVISIONS / REJECT"""


if __name__ == "__main__":
    sample_findings = {
        "deficiencies": [
            "DEFICIENCY 1: Written assent absent for ages 12-16. 45 CFR 46.408",
            "DEFICIENCY 2: Hepatic monitoring not in consent. ICH E6(R2) 4.8.10",
            "DEFICIENCY 3: BAA missing for CRO data sharing. HIPAA 45 CFR 164.308(b)(1)",
        ],
        "passes": ["PASS: Benefit assessment", "PASS: De-identification", "PASS: Data retention"],
        "total_deficiencies": 3,
        "requires_full_board": True,
    }
    
    result = asyncio.run(format_hitl_request(sample_findings, "PEDI-2026-0047", "EXPEDITED"))
    print(result)
    print("\n---\n")
    print(format_clarification_request(sample_findings))
