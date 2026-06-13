"""CommitteeAgent — IRB Committee Coordinator & HITL Enforcer

Framework: FastAPI (direct integration)
Model: Llama 3.1 70B via Featherless AI
Role: Aggregates findings from all specialist agents, enforces mandatory
      human IRB chair approval, and generates determination letters.
"""

import os
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

COMMITTEE_MODEL = "meta-llama/Llama-3.1-70B-Instruct"

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


async def aggregate_findings(room_messages: List[str]) -> Dict:
    """Aggregate all agent findings from Band room history."""
    deficiencies = []
    passes = []
    
    for msg in room_messages:
        # Parse deficiencies
        if "DEFICIENCY" in msg:
            lines = msg.split("\n")
            for line in lines:
                if line.strip().startswith("DEFICIENCY"):
                    deficiencies.append(line.strip())
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
    """Generate formal IRB determination letter using Llama 3.1."""
    try:
        response = await featherless_client.chat.completions.create(
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
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Determination letter generation failed: {str(e)}. Manual generation required."


async def format_hitl_request(findings: Dict, protocol_number: str) -> str:
    """Format the HITL request message for the Band room."""
    deficiency_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(findings["deficiencies"]))
    
    return f"""All findings aggregated. Invoking add_participant_service to add Dr. IRB Chair to this Band room...

@Dr.IRBChair — Full Board determination required.
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
    
    result = asyncio.run(format_hitl_request(sample_findings, "PEDI-2026-0047"))
    print(result)
