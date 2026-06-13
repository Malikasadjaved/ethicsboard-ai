import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

featherless_client = AsyncOpenAI(
    api_key=os.getenv("FEATHERLESS_API_KEY"),
    base_url="https://api.featherless.ai/v1"
)

async def ethics_review(protocol_summary: str) -> str:
    response = await featherless_client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        messages=[{
            "role": "user", 
            "content": f"""You are an IRB ethics specialist. Review this 
            research protocol summary for:
            1. Informed consent adequacy per 45 CFR 46
            2. Written assent requirements for minors (45 CFR 46.408)
            3. Risk disclosure completeness (ICH E6(R2) 4.8.10)
            4. Risk-benefit ratio justification
            
            Flag every deficiency with its regulatory citation.
            
            Protocol summary:
            {protocol_summary}"""
        }]
    )
    return response.choices[0].message.content
