"""
Confidence scoring for the Underwriter Agent.

Calculates overall confidence score based on data quality and coverage.
Confidence score reflects how reliable the analysis is, not the creditworthiness.

Confidence Factors (5 weighted components):
1. Document Quality (30%) - All documents parsed successfully
2. Data Completeness (25%) - All required fields populated
3. Cross-Validation Consistency (20%) - Declared vs detected data alignment
4. OSINT Coverage (15%) - Business validation or formal employment
5. IRS Deduction Count (10%) - Fewer deductions = higher confidence
"""

from decimal import Decimal
from typing import Optional
from app.core.state import AgentState


# ============================================================================
# Confidence Factor Weights
# ============================================================================

WEIGHT_DOCUMENT_QUALITY = 0.30
WEIGHT_DATA_COMPLETENESS = 0.25
WEIGHT_CROSS_VALIDATION = 0.20
WEIGHT_OSINT_COVERAGE = 0.15
WEIGHT_IRS_DEDUCTIONS = 0.10

# Minimum confidence floor (even with significant missing data)
MINIMUM_CONFIDENCE = 0.30

# Salary variance tolerance for cross-validation (±20%)
SALARY_VARIANCE_TOLERANCE = Decimal("0.20")


# ============================================================================
# Confidence Calculation Functions
# ============================================================================


def calculate_confidence(state: AgentState) -> float:
    """
    Calculate overall confidence score from agent state.

    Formula: confidence = Σ(factor_weight * factor_score)
    All factor scores are normalized to [0.0, 1.0]

    Args:
        state: Current agent state with all agent outputs

    Returns:
        Confidence score (0.0-1.0), minimum 0.30
    """
    # Calculate individual factor scores
    doc_quality_score = _calculate_document_quality_score(state)
    data_completeness_score = _calculate_data_completeness_score(state)
    cross_validation_score = _calculate_cross_validation_score(state)
    osint_coverage_score = _calculate_osint_coverage_score(state)
    irs_deduction_score = _calculate_irs_deduction_score(state)

    # Handle OSINT skip scenario (redistribute weight)
    if state.config.get("skip_osint", False):
        # Redistribute OSINT weight proportionally to other factors
        osint_weight = 0.0
        remaining_weight = 1.0 - WEIGHT_OSINT_COVERAGE
        doc_weight = WEIGHT_DOCUMENT_QUALITY / remaining_weight
        data_weight = WEIGHT_DATA_COMPLETENESS / remaining_weight
        cross_weight = WEIGHT_CROSS_VALIDATION / remaining_weight
        irs_weight = WEIGHT_IRS_DEDUCTIONS / remaining_weight
    else:
        doc_weight = WEIGHT_DOCUMENT_QUALITY
        data_weight = WEIGHT_DATA_COMPLETENESS
        cross_weight = WEIGHT_CROSS_VALIDATION
        osint_weight = WEIGHT_OSINT_COVERAGE
        irs_weight = WEIGHT_IRS_DEDUCTIONS

    # Weighted sum
    confidence = (
        doc_weight * doc_quality_score
        + data_weight * data_completeness_score
        + cross_weight * cross_validation_score
        + osint_weight * osint_coverage_score
        + irs_weight * irs_deduction_score
    )

    # Apply minimum confidence floor
    return max(confidence, MINIMUM_CONFIDENCE)


def _calculate_document_quality_score(state: AgentState) -> float:
    """
    Calculate document quality factor (30% weight).

    Criteria:
    - All uploaded documents were successfully parsed
    - No OCR errors or quality warnings

    Returns:
        Score 0.0-1.0
    """
    if not state.documents:
        return 0.0

    # Check documents_processed for errors
    total_docs = len(state.documents)
    if total_docs == 0:
        return 0.0

    processed_docs = len(state.documents_processed)

    # Check for document processing errors
    doc_errors = [
        error for error in state.errors
        if "document" in error.get("agent", "").lower()
    ]

    if doc_errors:
        # Partial penalty for document errors
        return max(0.5, (processed_docs / total_docs) * 0.8)

    # All documents processed successfully
    if processed_docs >= total_docs:
        return 1.0

    # Partial score based on processed ratio
    return processed_docs / total_docs


def _calculate_data_completeness_score(state: AgentState) -> float:
    """
    Calculate data completeness factor (25% weight).

    Criteria:
    - Required fields populated: salary, credit score, employment date
    - Bank statement parsed
    - Credit report available

    Returns:
        Score 0.0-1.0
    """
    score = 0.0
    total_components = 5

    # 1. Salary detected from bank statement
    if state.financial_analysis and state.financial_analysis.detected_salary_amount:
        score += 1.0

    # 2. Credit score available
    if state.financial_analysis and state.financial_analysis.credit_score:
        score += 1.0

    # 3. Bank account verified
    if state.financial_analysis and state.financial_analysis.bank_account_verified:
        score += 1.0

    # 4. Employment date available (from applicant data)
    if state.applicant.get("employment_start_date"):
        score += 1.0

    # 5. IRS score calculated (implies all inputs available)
    if state.irs_score:
        score += 1.0

    return score / total_components


def _calculate_cross_validation_score(state: AgentState) -> float:
    """
    Calculate cross-validation consistency factor (20% weight).

    Criteria:
    - Declared salary vs detected salary within ±20% tolerance
    - No major data inconsistencies

    Returns:
        Score 0.0-1.0
    """
    if not state.financial_analysis:
        return 0.5  # Neutral score if no financial analysis

    declared_salary = Decimal(str(state.applicant.get("declared_salary", 0)))
    detected_salary = state.financial_analysis.detected_salary_amount

    if not declared_salary or not detected_salary:
        return 0.5  # Neutral score if missing data

    # Calculate variance
    variance = abs(declared_salary - detected_salary) / declared_salary

    # Perfect match (within ±5%)
    if variance <= Decimal("0.05"):
        return 1.0

    # Within tolerance (±20%)
    if variance <= SALARY_VARIANCE_TOLERANCE:
        return 0.8

    # Outside tolerance (±20-50%)
    if variance <= Decimal("0.50"):
        return 0.4

    # Major discrepancy (>50%)
    return 0.0


def _calculate_osint_coverage_score(state: AgentState) -> float:
    """
    Calculate OSINT coverage factor (15% weight).

    Criteria:
    - Business found with good Digital Veracity Score (DVS), OR
    - Applicant is formal employee (skip OSINT validation)

    Returns:
        Score 0.0-1.0
    """
    # If OSINT was skipped via config, this factor is redistributed
    if state.config.get("skip_osint", False):
        return 0.0  # Weight redistributed by main function

    # Check if formal employee (can skip OSINT)
    employer = state.applicant.get("declared_employer", "")
    if employer and not any(keyword in employer.lower() for keyword in ["independiente", "cuenta propia", "freelance"]):
        # Formal employment, OSINT not critical
        return 0.8

    # Check OSINT findings
    if not state.osint_findings:
        return 0.3  # Low score if OSINT not executed

    # Use Digital Veracity Score as direct indicator
    dvs = state.osint_findings.digital_veracity_score
    return float(dvs)  # DVS is already 0.0-1.0


def _calculate_irs_deduction_score(state: AgentState) -> float:
    """
    Calculate IRS deduction count factor (10% weight).

    Criteria:
    - Fewer deductions = higher confidence
    - 0 deductions = 1.0, many deductions = lower score

    Returns:
        Score 0.0-1.0
    """
    if not state.irs_score:
        return 0.5  # Neutral if IRS not calculated

    deduction_count = len(state.irs_score.deductions)

    # No deductions = perfect score (100 IRS)
    if deduction_count == 0:
        return 1.0

    # 1-3 deductions = high confidence
    if deduction_count <= 3:
        return 0.9

    # 4-6 deductions = medium confidence
    if deduction_count <= 6:
        return 0.7

    # 7-9 deductions = low confidence
    if deduction_count <= 9:
        return 0.5

    # 10+ deductions = very low confidence (many issues detected)
    return 0.3


def get_confidence_breakdown(state: AgentState) -> dict[str, dict]:
    """
    Get detailed breakdown of confidence calculation.

    Useful for debugging and transparency.

    Args:
        state: Current agent state

    Returns:
        Dictionary with scores and weights per factor
    """
    return {
        "document_quality": {
            "score": _calculate_document_quality_score(state),
            "weight": WEIGHT_DOCUMENT_QUALITY,
            "description": "All documents parsed successfully",
        },
        "data_completeness": {
            "score": _calculate_data_completeness_score(state),
            "weight": WEIGHT_DATA_COMPLETENESS,
            "description": "Required fields populated",
        },
        "cross_validation": {
            "score": _calculate_cross_validation_score(state),
            "weight": WEIGHT_CROSS_VALIDATION,
            "description": "Declared vs detected data consistency",
        },
        "osint_coverage": {
            "score": _calculate_osint_coverage_score(state),
            "weight": WEIGHT_OSINT_COVERAGE,
            "description": "Business validation or formal employment",
        },
        "irs_deductions": {
            "score": _calculate_irs_deduction_score(state),
            "weight": WEIGHT_IRS_DEDUCTIONS,
            "description": "Fewer deductions = higher confidence",
        },
    }
