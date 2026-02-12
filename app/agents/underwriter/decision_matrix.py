"""
Decision matrix for the Underwriter Agent.

Implements the decision logic from PRD Section 5 (Agent 6: Underwriter).
Maps IRS scores and confidence levels to final credit decisions.

Business Rules (Approved 2026-02-12):
- IRS ≥85 + Confidence ≥85% → APPROVED
- IRS ≥85 + Confidence <85% → APPROVED_PENDING_REVIEW
- IRS 60-84 (any confidence) → MANUAL_REVIEW
- IRS <60 (any confidence) → REJECTED
- Loan amount >50,000 DOP → ALWAYS MANUAL_REVIEW (override)
"""

from decimal import Decimal
from typing import Literal

# ============================================================================
# Decision Thresholds (Stakeholder-Approved)
# ============================================================================

# IRS Score thresholds
IRS_SCORE_APPROVED = 85  # Minimum score for auto-approval
IRS_SCORE_MANUAL_REVIEW = 60  # Below this is auto-reject
IRS_SCORE_REJECTED = 60  # Threshold for rejection (inclusive)

# Confidence threshold for auto-approval
CONFIDENCE_THRESHOLD = 0.85

# High-amount threshold requiring manual review
HIGH_AMOUNT_THRESHOLD = Decimal("50000")  # DOP

# Decision types
DecisionType = Literal["APPROVED", "REJECTED",
                       "MANUAL_REVIEW", "APPROVED_PENDING_REVIEW"]


# ============================================================================
# Decision Functions
# ============================================================================


def make_decision(
    irs_score: int,
    confidence: float,
    loan_amount: Decimal,
) -> DecisionType:
    """
    Make final credit decision based on IRS score, confidence, and loan amount.

    Business Logic:
    1. High-amount override: loans >50K DOP always require manual review
    2. IRS-based decision matrix with confidence scoring
    3. Returns one of 4 decision types

    Args:
        irs_score: IRS score (0-100)
        confidence: Confidence score (0.0-1.0)
        loan_amount: Requested loan amount in DOP

    Returns:
        Decision: APPROVED, REJECTED, MANUAL_REVIEW, or APPROVED_PENDING_REVIEW

    Examples:
        >>> make_decision(90, 0.90, Decimal("40000"))
        'APPROVED'
        >>> make_decision(90, 0.90, Decimal("75000"))
        'MANUAL_REVIEW'  # High amount override
        >>> make_decision(90, 0.70, Decimal("40000"))
        'APPROVED_PENDING_REVIEW'  # Low confidence
        >>> make_decision(75, 0.85, Decimal("30000"))
        'MANUAL_REVIEW'  # Medium IRS score
        >>> make_decision(50, 0.90, Decimal("20000"))
        'REJECTED'  # Low IRS score
    """
    # High-amount override: Always manual review for loans >50K DOP
    if loan_amount > HIGH_AMOUNT_THRESHOLD:
        return "MANUAL_REVIEW"

    # IRS score below 60: Auto-reject (critical risk)
    if irs_score < IRS_SCORE_REJECTED:
        return "REJECTED"

    # IRS score 60-84: Manual review required (medium risk)
    if irs_score < IRS_SCORE_APPROVED:
        return "MANUAL_REVIEW"

    # IRS score ≥85: Approve with confidence check
    if confidence >= CONFIDENCE_THRESHOLD:
        return "APPROVED"
    else:
        return "APPROVED_PENDING_REVIEW"


def get_risk_level(irs_score: int) -> Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
    """
    Map IRS score to risk level.

    Args:
        irs_score: IRS score (0-100)

    Returns:
        Risk level: LOW, MEDIUM, HIGH, or CRITICAL
    """
    if irs_score >= 85:
        return "LOW"
    elif irs_score >= 70:
        return "MEDIUM"
    elif irs_score >= 60:
        return "HIGH"
    else:
        return "CRITICAL"


def requires_human_review(decision: DecisionType) -> bool:
    """
    Determine if decision requires human review.

    Args:
        decision: Decision type

    Returns:
        True if human review is required
    """
    return decision in ("MANUAL_REVIEW", "APPROVED_PENDING_REVIEW")


def calculate_suggested_amount(
    irs_score: int,
    requested_amount: Decimal,
    payment_capacity: Decimal,
    term_months: int,
) -> Decimal | None:
    """
    Calculate suggested loan amount for MEDIUM risk cases.

    Business Rule (Approved 2026-02-12):
    - ALWAYS suggest reduced amounts for MEDIUM risk (IRS 60-84)
    - Calculate: suggested_amount = payment_capacity * term_months * 0.8
    - Never extend term (reduce amount instead)

    Args:
        irs_score: IRS score (0-100)
        requested_amount: Requested loan amount in DOP
        payment_capacity: Monthly payment capacity in DOP
        term_months: Loan term in months

    Returns:
        Suggested amount in DOP, or None if no suggestion needed
    """
    # Only suggest for MEDIUM risk (60-84 score range)
    if irs_score < 60 or irs_score >= 85:
        return None

    # Calculate maximum affordable amount with 80% buffer
    max_affordable = payment_capacity * Decimal(term_months) * Decimal("0.8")

    # Only suggest if it's less than requested amount
    if max_affordable < requested_amount:
        return max_affordable

    # For MEDIUM risk, always suggest reduced amount even if they can afford it
    # This is conservative lending for medium-risk profiles
    return max_affordable


def get_decision_flags(
    decision: DecisionType,
    irs_score: int,
    confidence: float,
    loan_amount: Decimal,
) -> list[str]:
    """
    Generate flags explaining why this decision was made.

    Args:
        decision: Final decision
        irs_score: IRS score
        confidence: Confidence score
        loan_amount: Loan amount

    Returns:
        List of flag strings
    """
    flags = []

    # High amount flag
    if loan_amount > HIGH_AMOUNT_THRESHOLD:
        flags.append(
            f"HIGH_AMOUNT: Loan amount DOP {loan_amount:,.2f} exceeds threshold (DOP {HIGH_AMOUNT_THRESHOLD:,.2f}), requires senior approval")

    # Low confidence flag
    if confidence < CONFIDENCE_THRESHOLD:
        flags.append(
            f"LOW_CONFIDENCE: Confidence {confidence:.1%} below threshold ({CONFIDENCE_THRESHOLD:.0%}), requires verification")

    # Medium risk flag
    if 60 <= irs_score < 85:
        flags.append(
            f"MEDIUM_RISK: IRS score {irs_score} indicates medium risk profile")

    # Critical risk flag
    if irs_score < 60:
        flags.append(
            f"CRITICAL_RISK: IRS score {irs_score} below acceptable threshold")

    return flags
