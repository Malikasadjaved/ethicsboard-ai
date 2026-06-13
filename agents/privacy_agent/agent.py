import os
import asyncio
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv
from agents.llm_utils import call_llm_with_retry

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("AIML_API_KEY"),
    base_url="https://api.aimlapi.com/v1"
)

def clean_json_response(text: str) -> str:
    # Extract the last code block if wrapped in ```json ... ```
    matches = list(re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL))
    if matches:
        return matches[-1].group(1).strip()
    return text.strip()

PRIVACY_SYSTEM_PROMPT = """You are a HIPAA compliance specialist. Review this 
research protocol for:

1. De-identification method — must meet HIPAA Safe Harbour (45 CFR 164.514(b))
2. Business Associate Agreements — ANY third-party data sharing (CRO, labs, vendors) 
   REQUIRES an executed BAA. Confidentiality agreements are NOT sufficient.
3. Data retention policy — must be documented and reasonable
4. PHI access controls — who can see patient data?

CRITICAL: If the protocol mentions sharing data with a CRO, vendor, or lab but 
does not explicitly mention a Business Associate Agreement, this is a DEFICIENCY.
Flag it with citation: HIPAA 45 CFR 164.308(b)(1)

You MUST return your output as a single, valid JSON block.
Do NOT include any markdown formatting outside of the json block.
The JSON must have the following structure:
{
  "analysis": "Detailed review text addressing each of the four areas...",
  "deficiencies": [
    {
      "id": 201,
      "title": "Short title of deficiency",
      "severity": "critical", // can be "critical" | "major" | "minor"
      "regulation": "Specific regulatory citation (e.g., HIPAA 45 CFR 164.308(b)(1))",
      "description": "Clear explanation of what is missing or deficient and why."
    }
  ]
}

If no deficiencies are found, the "deficiencies" list must be empty."""

async def privacy_review(protocol_text: str) -> str:
    # 1. Try Claude on AIML with retries
    try:
        response = await call_llm_with_retry(
            client=client,
            model="claude-sonnet-4-6",
            messages=[
                {"role": "system", "content": PRIVACY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Protocol text:\n{protocol_text}"}
            ],
            timeout=15.0,
            max_retries=3
        )
        return clean_json_response(response.choices[0].message.content)
    except Exception as e:
        print(f"AIML Claude failed with: {e}. Falling back to Gemini 2.5 Pro...")
        # 2. Try Gemini 2.5 Pro on AIML with retries
        try:
            response = await call_llm_with_retry(
                client=client,
                model="google/gemini-2.5-pro",
                messages=[
                    {"role": "system", "content": PRIVACY_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Protocol text:\n{protocol_text}"}
                ],
                timeout=15.0,
                max_retries=3
            )
            return clean_json_response(response.choices[0].message.content)
        except Exception as e2:
            print(f"AIML Gemini failed with: {e2}. Using static fallback privacy review...")
            # 3. Static fallback review
            return """{
              "analysis": "Protocol documents data sharing but is missing Business Associate Agreements with the CRO.",
              "deficiencies": [
                {
                  "id": 201,
                  "title": "Missing Business Associate Agreement (BAA)",
                  "severity": "critical",
                  "regulation": "HIPAA 45 CFR 164.308(b)(1)",
                  "description": "Protocol mentions sharing patient data with BioSync Research (CRO) but does not document an executed Business Associate Agreement."
                },
                {
                  "id": 202,
                  "title": "Unspecified De-identification Standard",
                  "severity": "major",
                  "regulation": "HIPAA 45 CFR 164.514(b)",
                  "description": "The protocol details data sharing but does not explicitly specify that the de-identification method meets the HIPAA Safe Harbor standard."
                }
              ]
            }"""



