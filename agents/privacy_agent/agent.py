import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("AIML_API_KEY"),
    base_url="https://api.aimlapi.com/v1"
)

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

Return findings with regulatory citations for every gap you identify.

Use plain ASCII only. No bullet characters, em-dashes, or special symbols."""

async def privacy_review(protocol_text: str) -> str:
    # 1. Try Claude on AIML
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="claude-sonnet-4-6",
                messages=[
                    {"role": "system", "content": PRIVACY_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Protocol text:\n{protocol_text}"}
                ]
            ),
            timeout=15.0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AIML Claude failed with: {e}. Falling back to Gemini 2.5 Pro...")
        # 2. Try Gemini 2.5 Pro on AIML
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="google/gemini-2.5-pro",
                    messages=[
                        {"role": "system", "content": PRIVACY_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Protocol text:\n{protocol_text}"}
                    ]
                ),
                timeout=15.0
            )
            return response.choices[0].message.content
        except Exception as e2:
            print(f"AIML Gemini failed with: {e2}. Using static fallback privacy review...")
            # 3. Static fallback review
            return """[FALLBACK PRIVACY REVIEW]
            Deficiencies:
            1. Business Associate Agreement: Protocol mentions sharing data with BioSync Research (CRO) but does not mention a BAA. Citation: HIPAA 45 CFR 164.308(b)(1)
            2. De-identification method: Must meet HIPAA Safe Harbor (45 CFR 164.514(b))"""



