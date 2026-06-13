import os
os.environ["AIML_API_KEY"] = "mock-aiml-key"
os.environ["FEATHERLESS_API_KEY"] = "mock-featherless-key"

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Import functions to test
from agents.protocol_agent.agent import run_protocol_analysis, extract_protocol_data, format_summary, ProtocolState
from agents.ethics_agent.agent import run_ethics_review
from agents.privacy_agent.agent import run_privacy_review
from agents.committee_agent.agent import aggregate_findings, generate_determination_letter, format_hitl_request

# --- ProtocolAgent Tests ---

@pytest.mark.asyncio
async def test_protocol_agent_extraction():
    # Mock response from AI/ML API (Gemini 2.5 Pro)
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_json_content = """{
      "study_title": "Test Study Title",
      "protocol_number": "PEDI-2026-TEST",
      "phase": "Phase II",
      "sponsor": "Sponsor Inc.",
      "principal_investigator": "Dr. Test PI",
      "population": {
        "description": "Pediatric patients",
        "age_range": "8-16",
        "is_vulnerable": true,
        "vulnerable_category": "minors"
      },
      "risk_classification": "GREATER THAN MINIMAL RISK",
      "regulatory_basis": "45 CFR 46.405",
      "consent_procedures": {
        "adult_consent": "Written parent consent",
        "assent_procedure": "Verbal 8-11, missing 12-16",
        "waiver_requested": false
      },
      "data_handling": {
        "de_identification_method": "Coded ID",
        "data_sharing": "BioSync CRO",
        "retention_period": "15 years"
      },
      "review_type_recommended": "FULL BOARD"
    }"""
    
    mock_message.content = mock_json_content
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Mock the AsyncOpenAI completions create call
    with patch("agents.protocol_agent.agent.aiml_client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        # Test extract_protocol_data directly
        initial_state: ProtocolState = {
            "pdf_text": "Sample protocol content",
            "extracted_data": None,
            "risk_classification": None,
            "review_type": None,
            "summary": None,
            "error": None,
        }
        
        result_state = await extract_protocol_data(initial_state)
        
        assert result_state["error"] is None
        assert result_state["extracted_data"]["study_title"] == "Test Study Title"
        assert result_state["risk_classification"] == "GREATER THAN MINIMAL RISK"
        assert result_state["review_type"] == "FULL BOARD"
        
        # Test format_summary
        final_state = await format_summary(result_state)
        assert "@EthicsAgent" in final_state["summary"]
        assert "PEDI-2026-TEST" in final_state["summary"]
        assert "VULNERABLE" in final_state["summary"]

# --- EthicsAgent Tests ---

@pytest.mark.asyncio
async def test_ethics_agent_review():
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = "DEFICIENCY 1: Missing Assent. 45 CFR 46.408 — No assent form for 12-16.\nPASS: Risk-benefit ratio is justified.\nBenefit assessment: PASS.\n@PrivacyAgent — Please review."
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    with patch("agents.ethics_agent.agent.featherless_client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        result = await run_ethics_review("Sample context summary")
        assert "Ethics review complete" in result
        assert "DEFICIENCY 1: Missing Assent" in result
        assert "@PrivacyAgent" in result

# --- PrivacyAgent Tests ---

@pytest.mark.asyncio
async def test_privacy_agent_review():
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = "DEFICIENCY 1: Missing BAA. 45 CFR 164.308 — No BAA with CRO.\nPASS: Retention is compliant.\n@CommitteeAgent — 1 ethics deficiencies + 1 privacy gap."
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    with patch("agents.privacy_agent.agent.aiml_client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        result = await run_privacy_review("Sample context summary")
        assert "Data governance review complete" in result
        assert "DEFICIENCY 1: Missing BAA" in result
        assert "@CommitteeAgent" in result

# --- CommitteeAgent Tests ---

@pytest.mark.asyncio
async def test_committee_agent_aggregation():
    # Test aggregation function
    room_messages = [
        "Ethics review complete.\nDEFICIENCY 1: Missing Assent. 45 CFR 46.408\nPASS: Risk-benefit ratio.",
        "Data governance review complete.\nDEFICIENCY 2: Missing BAA. HIPAA 45 CFR 164.308(b)(1)\nPASS: Security safeguards."
    ]
    
    findings = await aggregate_findings(room_messages)
    assert findings["total_deficiencies"] == 2
    assert findings["requires_full_board"] is True
    assert findings["deficiencies"][0] == "DEFICIENCY 1: Missing Assent. 45 CFR 46.408"
    assert findings["deficiencies"][1] == "DEFICIENCY 2: Missing BAA. HIPAA 45 CFR 164.308(b)(1)"
    assert len(findings["passes"]) == 2

@pytest.mark.asyncio
async def test_committee_agent_determination():
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = "IRB DETERMINATION LETTER\nProtocol: PEDI-2026-TEST\nStatus: REVISIONS REQUIRED"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    with patch("agents.committee_agent.agent.featherless_client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        result = await generate_determination_letter(
            review_record="Review context",
            decision="revisions_required",
            chair_comments="Please fix BAA"
        )
        assert "IRB DETERMINATION LETTER" in result
        assert "REVISIONS REQUIRED" in result

@pytest.mark.asyncio
async def test_committee_agent_hitl_format():
    findings = {
        "deficiencies": [
            "DEFICIENCY 1: Missing Assent. 45 CFR 46.408",
            "DEFICIENCY 2: Missing BAA. HIPAA 45 CFR 164.308"
        ],
        "total_deficiencies": 2
    }
    
    result = await format_hitl_request(findings, "PEDI-2026-TEST")
    assert "@Dr.IRBChair" in result
    assert "PEDI-2026-TEST" in result
    assert "2 deficiencies identified" in result
