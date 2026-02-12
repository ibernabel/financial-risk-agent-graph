"""
Business rule definitions and constants for IRS Engine.

Defines all deduction rules for the 5 scoring variables (A-E) and thresholds.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DeductionRule:
    """Immutable deduction rule definition."""

    rule_id: str
    variable: str
    max_deduction: int
    flag_name: str
    description: str


# =============================================================================
# VARIABLE A: CREDIT HISTORY (25 points max)
# =============================================================================

RULE_A01_POOR_CREDIT = DeductionRule(
    rule_id="A-01",
    variable="credit_history",
    max_deduction=15,
    flag_name="POOR_CREDIT_HISTORY",
    description="Credit score below 600",
)

RULE_A02_FAIR_CREDIT = DeductionRule(
    rule_id="A-02",
    variable="credit_history",
    max_deduction=7,
    flag_name="FAIR_CREDIT_HISTORY",
    description="Credit score between 600-700",
)

RULE_A03_EXCESSIVE_INQUIRIES = DeductionRule(
    rule_id="A-03",
    variable="credit_history",
    max_deduction=5,
    flag_name="EXCESSIVE_INQUIRIES",
    description="More than 5 credit inquiries in last 6 months",
)

RULE_A04_ACTIVE_DELINQUENCY = DeductionRule(
    rule_id="A-04",
    variable="credit_history",
    max_deduction=10,
    flag_name="ACTIVE_DELINQUENCY",
    description="Active delinquencies on credit report",
)

RULE_A05_RISING_DEBT = DeductionRule(
    rule_id="A-05",
    variable="credit_history",
    max_deduction=3,
    flag_name="RISING_DEBT",
    description="Debt trend increasing",
)

# =============================================================================
# VARIABLE B: PAYMENT CAPACITY (25 points max)
# =============================================================================

RULE_B01_CRITICAL_CASH_FLOW = DeductionRule(
    rule_id="B-01",
    variable="payment_capacity",
    max_deduction=20,
    flag_name="CRITICAL_CASH_FLOW",
    description="Cash flow ratio below 10%",
)

RULE_B02_TIGHT_CASH_FLOW = DeductionRule(
    rule_id="B-02",
    variable="payment_capacity",
    max_deduction=10,
    flag_name="TIGHT_CASH_FLOW",
    description="Cash flow ratio between 10-20%",
)

RULE_B03_LOW_INCOME = DeductionRule(
    rule_id="B-03",
    variable="payment_capacity",
    max_deduction=5,
    flag_name="LOW_INCOME",
    description="Salary below minimum wage + 10%",
)

RULE_B04_HIGH_DEPENDENCY_RATIO = DeductionRule(
    rule_id="B-04",
    variable="payment_capacity",
    max_deduction=10,
    flag_name="HIGH_DEPENDENCY_RATIO",
    description="More than 3 dependents with salary below 35,000 DOP",
)

# =============================================================================
# VARIABLE C: STABILITY (15 points max)
# =============================================================================

RULE_C01_PROBATION_PERIOD = DeductionRule(
    rule_id="C-01",
    variable="stability",
    max_deduction=10,
    flag_name="PROBATION_PERIOD",
    description="Employment tenure less than 3 months",
)

RULE_C02_SHORT_TENURE = DeductionRule(
    rule_id="C-02",
    variable="stability",
    max_deduction=5,
    flag_name="SHORT_TENURE",
    description="Employment tenure between 3-12 months",
)

RULE_C03_RECENT_MOVE = DeductionRule(
    rule_id="C-03",
    variable="stability",
    max_deduction=5,
    flag_name="RECENT_MOVE",
    description="Residence tenure less than 6 months",
)

RULE_C04_ADDRESS_INCONSISTENCY = DeductionRule(
    rule_id="C-04",
    variable="stability",
    max_deduction=5,
    flag_name="ADDRESS_INCONSISTENCY",
    description="Address mismatch between declared and bills",
)

# =============================================================================
# VARIABLE D: COLLATERAL (15 points max)
# =============================================================================

RULE_D01_NO_ASSETS = DeductionRule(
    rule_id="D-01",
    variable="collateral",
    max_deduction=3,
    flag_name="NO_ASSETS",
    description="No assets (vehicle/property) declared",
)

RULE_D02_INSUFFICIENT_GUARANTEE = DeductionRule(
    rule_id="D-02",
    variable="collateral",
    max_deduction=5,
    flag_name="INSUFFICIENT_GUARANTEE",
    description="Severance (prestaciones) less than 20% of loan amount",
)

# =============================================================================
# VARIABLE E: PAYMENT MORALITY (20 points max)
# =============================================================================

RULE_E01_FAST_WITHDRAWAL = DeductionRule(
    rule_id="E-01",
    variable="payment_morality",
    max_deduction=5,
    flag_name="FAST_WITHDRAWAL",
    description="Fast withdrawal pattern detected (>90% salary withdrawn within 24h)",
)

RULE_E02_INFORMAL_LENDER = DeductionRule(
    rule_id="E-02",
    variable="payment_morality",
    max_deduction=15,
    flag_name="INFORMAL_LENDER_DETECTED",
    description="Informal lender pattern detected",
)

RULE_E03_DATA_INCONSISTENCY = DeductionRule(
    rule_id="E-03",
    variable="payment_morality",
    max_deduction=10,
    flag_name="DATA_INCONSISTENCY",
    description="Interview data inconsistency detected",
)

RULE_E04_LOCATION_MISMATCH = DeductionRule(
    rule_id="E-04",
    variable="payment_morality",
    max_deduction=10,
    flag_name="LOCATION_MISMATCH",
    description="Address mismatch between declared and consumption zone",
)

# =============================================================================
# VARIABLE WEIGHTS
# =============================================================================

VARIABLE_WEIGHTS = {
    "credit_history": 25,
    "payment_capacity": 25,
    "stability": 15,
    "collateral": 15,
    "payment_morality": 20,
}

# =============================================================================
# THRESHOLDS
# =============================================================================

# Credit History thresholds
CREDIT_SCORE_POOR: int = 600
CREDIT_SCORE_FAIR: int = 700
EXCESSIVE_INQUIRIES_THRESHOLD: int = 5
INQUIRIES_LOOKBACK_MONTHS: int = 6

# Payment Capacity thresholds
CASH_FLOW_CRITICAL_PCT: Decimal = Decimal("0.10")  # 10%
CASH_FLOW_TIGHT_PCT: Decimal = Decimal("0.20")  # 20%
MINIMUM_WAGE_BUFFER_PCT: Decimal = Decimal("0.10")  # 10%
HIGH_DEPENDENCY_THRESHOLD: int = 3
HIGH_DEPENDENCY_SALARY_THRESHOLD: Decimal = Decimal("35000")

# Stability thresholds
PROBATION_PERIOD_MONTHS: int = 3
SHORT_TENURE_MONTHS: int = 12
RECENT_MOVE_MONTHS: int = 6

# Collateral thresholds
SEVERANCE_LOAN_RATIO_THRESHOLD: Decimal = Decimal("0.20")  # 20%

# Risk level thresholds
RISK_LEVEL_LOW_THRESHOLD: int = 85
RISK_LEVEL_MEDIUM_THRESHOLD: int = 70
RISK_LEVEL_HIGH_THRESHOLD: int = 60
