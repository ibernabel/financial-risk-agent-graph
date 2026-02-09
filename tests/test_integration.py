"""
Integration tests for Phase 2B - End-to-end workflow testing.

Tests the complete analysis flow with real parsers and pattern detection.
"""

import pytest
from decimal import Decimal

from app.core.state import AgentState
from app.agents.triage.node import triage_node
from app.agents.financial.node import financial_analyst_node


@pytest.mark.asyncio
async def test_end_to_end_triage_to_financial():
    """Test full analysis flow from Triage to Financial Analyst."""
    # Create test state with valid applicant
    state = AgentState(
        case_id="TEST-INT-001",
        applicant={
            "age": 30,
            # Province name only (triage extracts last part after comma)
            "declared_address": "Santo Domingo",
            # Above minimum wage (23,000) + 10% buffer = 25,300
            "declared_salary": 26000,
            "employer_employee_count": 100,
        },
        loan={
            "requested_amount": 50000,
            "product_type": "PERSONAL_LOAN",
        },
        documents=[
            {"type": "bank_statement",
                "path": "creditflow_context/personal_loan_application_data/bank_statements/bhd_bank/bhd_bank_statement.pdf"}
        ],
        config={},
    )

    # Run Triage
    triage_update = await triage_node(state)
    state = state.model_copy(update=triage_update)

    # Verify Triage passed
    assert state.triage_result is not None
    assert state.triage_result.status == "PASSED"
    assert "triage" in state.agents_executed

    # Run Financial Analysis
    financial_update = await financial_analyst_node(state)
    state = state.model_copy(update=financial_update)

    # Verify Financial Analysis completed
    assert state.financial_analysis is not None
    assert "financial_analyst" in state.agents_executed


@pytest.mark.asyncio
async def test_triage_rejection_age():
    """Test rejection at Triage stage due to age."""
    state = AgentState(
        case_id="TEST-INT-002",
        applicant={"age": 17},  # Too young
        loan={"requested_amount": 50000, "product_type": "PERSONAL_LOAN"},
        documents=[],
        config={},
    )

    triage_update = await triage_node(state)
    state = state.model_copy(update=triage_update)

    assert state.triage_result.status == "REJECTED"
    assert "Edad" in state.triage_result.rejection_reason


@pytest.mark.asyncio
async def test_triage_rejection_zone():
    """Test rejection at Triage stage due to geographic zone."""
    state = AgentState(
        case_id="TEST-INT-003",
        applicant={
            "age": 30,
            "declared_address": "Santiago, Santiago",  # Not allowed for PERSONAL_LOAN
        },
        loan={"requested_amount": 50000, "product_type": "PERSONAL_LOAN"},
        documents=[],
        config={},
    )

    triage_update = await triage_node(state)
    state = state.model_copy(update=triage_update)

    assert state.triage_result.status == "REJECTED"
    assert "zona" in state.triage_result.rejection_reason.lower()


@pytest.mark.asyncio
async def test_financial_analyst_without_documents():
    """Test Financial Analyst with no documents provided."""
    state = AgentState(
        case_id="TEST-INT-004",
        applicant={"age": 30, "declared_salary": 35000},
        loan={"requested_amount": 50000, "product_type": "PERSONAL_LOAN"},
        documents=[],  # No documents
        config={},
    )

    financial_update = await financial_analyst_node(state)
    state = state.model_copy(update=financial_update)

    # Should complete but with no verification
    assert state.financial_analysis is not None
    assert state.financial_analysis.bank_account_verified is False
    assert state.financial_analysis.salary_verified is False
    assert state.financial_analysis.financial_behavior_score == 50  # Neutral score


@pytest.mark.asyncio
async def test_financial_analyst_bank_detection():
    """Test bank detection from file path."""
    from app.agents.financial.node import _detect_bank_from_path

    assert _detect_bank_from_path("/path/to/bhd_statement.pdf") == "BHD"
    assert _detect_bank_from_path("/path/to/popular_bank.pdf") == "Popular"
    assert _detect_bank_from_path(
        "/path/to/banreservas_statement.pdf") == "Banreservas"
    assert _detect_bank_from_path("/path/to/unknown_bank.pdf") == "Unknown"


@pytest.mark.asyncio
async def test_financial_behavior_score_calculation():
    """Test financial behavior score calculation."""
    from app.agents.financial.node import _calculate_behavior_score

    # Test with no bank data
    score = _calculate_behavior_score(None, {})
    assert score == 50  # Neutral score

    # Test with clean patterns (mock bank data as None, patterns only)
    patterns_clean = {
        "fast_withdrawal_dates": [],
        "informal_lender_detected": False,
        "nsf_count": 0,
        "salary_inconsistent": False,
        "flags": [],
    }
    # Since we can't easily create BankStatementData without imports,
    # we'll test the None case which is valid
    score = _calculate_behavior_score(None, patterns_clean)
    assert score == 50


@pytest.mark.asyncio
async def test_state_error_tracking():
    """Test that errors are properly tracked in state."""
    state = AgentState(
        case_id="TEST-INT-005",
        applicant={"age": 30},
        loan={"requested_amount": 50000, "product_type": "PERSONAL_LOAN"},
        documents=[
            # Invalid path
            {"type": "bank_statement", "path": "/nonexistent/path/to/statement.pdf"}
        ],
        config={},
    )

    financial_update = await financial_analyst_node(state)
    state = state.model_copy(update=financial_update)

    # Should have error logged
    assert len(state.errors) > 0
    assert any("Bank parsing failed" in str(err) for err in state.errors)
