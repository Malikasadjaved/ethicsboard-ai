import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.protocol_agent.agent import extract_pdf_text, analyze_protocol
from agents.ethics_agent.agent import ethics_review
from agents.privacy_agent.agent import privacy_review

async def main():
    file_path = r"D:\Hackathone band\demo\IRB_Protocol_PEDI-2026-0047.pdf"
    
    with open("results.txt", "w", encoding="utf-8") as out:
        out.write("--- 1. Extracting PDF ---\n")
        pdf_text = extract_pdf_text(file_path)
        out.write(f"Extracted {len(pdf_text)} characters.\n\n")
        
        out.write("--- 2. ProtocolAgent Analysis ---\n")
        protocol_summary = await analyze_protocol(pdf_text)
        out.write(protocol_summary + "\n\n")
        
        out.write("--- 3. EthicsAgent Review ---\n")
        ethics_result = await ethics_review(protocol_summary)
        out.write(ethics_result + "\n\n")
        
        out.write("--- 4. PrivacyAgent Review ---\n")
        privacy_result = await privacy_review(pdf_text)
        out.write(privacy_result + "\n\n")
        
        out.write("--- TEST COMPLETE ---\n")

if __name__ == "__main__":
    asyncio.run(main())
