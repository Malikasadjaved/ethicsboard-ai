"""Unit tests for EthicsBoard AI committee coordination logic.

These tests cover the pure, network-free decision logic that drives the
regulatory workflow: review-track extraction, finding aggregation/dedup,
the agent-to-agent challenge prompt, and the risk-based HITL routing
(including the 45 CFR 46.110(b) expedited -> full-board escalation).

They run with plain `pytest` (no live API keys, no pytest-asyncio plugin) —
async functions are driven via asyncio.run.
"""

import os

# Committee agent constructs an AsyncOpenAI client at import time; give it a
# dummy key so import never depends on a real environment.
os.environ.setdefault("FEATHERLESS_API_KEY", "test-key")

import asyncio

from agents.committee_agent.agent import (
    aggregate_findings,
    extract_review_track,
    format_clarification_request,
    format_hitl_request,
    _parse_json_deficiencies,
)


# --- extract_review_track ---

def test_extract_review_track_expedited():
    msgs = ["...", "RISK: MINIMAL -> REVIEW TRACK: EXPEDITED (45 CFR 46.110)"]
    assert extract_review_track(msgs) == "EXPEDITED"


def test_extract_review_track_full_board():
    msgs = ["REVIEW TRACK: FULL BOARD (45 CFR 46.108)"]
    assert extract_review_track(msgs) == "FULL_BOARD"


def test_extract_review_track_defaults_to_full_board_when_absent():
    # Safe default: when no track line is present, require the convened board.
    assert extract_review_track(["no track line here"]) == "FULL_BOARD"


# --- _parse_json_deficiencies ---

def test_parse_json_deficiencies_extracts_array():
    msg = (
        'ETHICS REVIEW FINDINGS\n'
        '{"analysis": "ok", "deficiencies": ['
        '{"id": 101, "title": "Missing assent", "regulation": "45 CFR 46.408", "severity": "major"}'
        ']}'
    )
    out = _parse_json_deficiencies(msg)
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["regulation"] == "45 CFR 46.408"


def test_parse_json_deficiencies_returns_none_without_json():
    assert _parse_json_deficiencies("plain text, no json object") is None


# --- aggregate_findings ---

def test_aggregate_findings_parses_json_and_dedupes():
    json_block = (
        '{"deficiencies": ['
        '{"id": 1, "title": "Missing Assent", "regulation": "45 CFR 46.408", "severity": "major"},'
        '{"id": 2, "title": "Missing BAA", "regulation": "HIPAA 45 CFR 164.308(b)(1)", "severity": "critical"}'
        ']}'
    )
    # Same finding posted twice in the room must only be counted once.
    findings = asyncio.run(aggregate_findings([json_block, json_block]))
    assert findings["total_deficiencies"] == 2
    assert findings["requires_full_board"] is True


def test_aggregate_findings_parses_legacy_line_format():
    msgs = [
        "ETHICS REVIEW FINDINGS\nDEFICIENCY 1: Missing Assent. 45 CFR 46.408\nPASS: Risk-benefit ratio.",
        "PRIVACY REVIEW FINDINGS\nDEFICIENCY 2: Missing BAA. HIPAA 45 CFR 164.308(b)(1)\nPASS: Retention policy.",
    ]
    findings = asyncio.run(aggregate_findings(msgs))
    assert findings["total_deficiencies"] == 2
    assert len(findings["passes"]) == 2


def test_aggregate_findings_clean_protocol_requires_no_board():
    findings = asyncio.run(aggregate_findings(["PRIVACY REVIEW FINDINGS\nPASS: All clear."]))
    assert findings["total_deficiencies"] == 0
    assert findings["requires_full_board"] is False


# --- format_clarification_request (agent-to-agent challenge) ---

def test_format_clarification_request_targets_ethics_with_top_finding():
    findings = {"deficiencies": ["DEFICIENCY 1: Missing Assent. 45 CFR 46.408"], "total_deficiencies": 1}
    out = format_clarification_request(findings)
    assert out.lstrip().startswith("CLARIFICATION REQUEST")
    assert "@ethics_agent" in out
    assert "Missing Assent" in out


# --- format_hitl_request (risk-based routing + escalation) ---

def test_hitl_expedited_with_deficiencies_escalates_to_full_board():
    findings = {"deficiencies": ["DEFICIENCY 1: x"], "total_deficiencies": 1}
    out = asyncio.run(format_hitl_request(findings, "PEDI-2026-0047", review_track="EXPEDITED"))
    assert "ESCALATION" in out
    assert "FULL BOARD" in out
    assert "@Dr.IRBChair" in out


def test_hitl_expedited_clean_uses_designated_reviewer():
    findings = {"deficiencies": [], "total_deficiencies": 0}
    out = asyncio.run(format_hitl_request(findings, "PEDI-2026-0047", review_track="EXPEDITED"))
    assert "EXPEDITED determination requested" in out
    assert "ESCALATION" not in out


def test_hitl_full_board_default():
    findings = {"deficiencies": ["DEFICIENCY 1: x", "DEFICIENCY 2: y"], "total_deficiencies": 2}
    out = asyncio.run(format_hitl_request(findings, "PEDI-2026-0047", review_track="FULL_BOARD"))
    assert "Full Board determination required" in out
    assert "2 deficiencies identified" in out
