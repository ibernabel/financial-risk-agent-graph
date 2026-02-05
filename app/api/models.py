"""
API request and response models using Pydantic.

Defines the contract between the API and clients.
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# Request Models
# ============================================================================


class ApplicantData(BaseModel):
    """Applicant personal information."""

    id: str = Field(description="National ID (Cédula)")
    full_name: str = Field(description="Full legal name")
    date_of_birth: str = Field(description="Date of birth (YYYY-MM-DD)")
    declared_salary: float = Field(description="Monthly salary in DOP", gt=0)
    declared_address: str = Field(description="Full address")
    declared_employer: str = Field(description="Employer name")
    dependents_count: int = Field(
        default=0, description="Number of dependents", ge=0)
    email: Optional[EmailStr] = Field(
        default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")


class LoanData(BaseModel):
    """Loan request details."""

    requested_amount: float = Field(
        description="Requested loan amount in DOP", ge=5000, le=100000
    )
    term_months: int = Field(description="Loan term in months", ge=6, le=60)
    product_type: Literal["PERSONAL_LOAN", "SAVINGS", "MORTGAGE", "AUTO"] = Field(
        description="Loan product type"
    )


class DocumentData(BaseModel):
    """Document upload information."""

    type: Literal["bank_statement", "labor_letter", "id_card", "credit_report"] = Field(
        description="Document type"
    )
    url: str = Field(description="Document URL (S3 or similar)")
    bank_name: Optional[str] = Field(
        default=None, description="Bank name for bank statements"
    )


class AnalysisConfig(BaseModel):
    """Analysis configuration options."""

    force_reanalysis: bool = Field(
        default=False, description="Force reanalysis even if cached result exists"
    )
    skip_osint: bool = Field(default=False, description="Skip OSINT research")
    timeout_seconds: int = Field(
        default=60, description="Maximum execution time", ge=10, le=300)


class AnalysisRequest(BaseModel):
    """Complete analysis request payload."""

    case_id: str = Field(description="Unique case identifier")
    applicant: ApplicantData
    loan: LoanData
    documents: list[DocumentData] = Field(
        description="List of uploaded documents")
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "case_id": "REQ-2026-001",
                "applicant": {
                    "id": "001-XXXXXXX-X",
                    "full_name": "Juan Pérez",
                    "date_of_birth": "1988-12-30",
                    "declared_salary": 35000.0,
                    "declared_address": "Calle 4, Ensanche Ozama, SDE",
                    "declared_employer": "Empresa XYZ SRL",
                    "dependents_count": 2,
                },
                "loan": {
                    "requested_amount": 75000.0,
                    "term_months": 24,
                    "product_type": "PERSONAL_LOAN",
                },
                "documents": [
                    {
                        "type": "bank_statement",
                        "bank_name": "bhd",
                        "url": "https://storage.example.com/cases/001/bhd_stmt.pdf",
                    }
                ],
                "config": {"force_reanalysis": False, "skip_osint": False},
            }
        }


# ============================================================================
# Response Models
# ============================================================================


class IRSBreakdown(BaseModel):
    """IRS score breakdown by variable."""

    credit_history: int = Field(description="Credit history score component")
    payment_capacity: int = Field(
        description="Payment capacity score component")
    stability: int = Field(description="Stability score component")
    collateral: int = Field(description="Collateral score component")
    payment_morality: int = Field(
        description="Payment morality score component")


class OSINTValidation(BaseModel):
    """OSINT validation results."""

    business_found: bool
    digital_veracity_score: float = Field(ge=0.0, le=1.0)
    sources_checked: list[str]


class AnalysisResult(BaseModel):
    """Analysis result with decision and scoring."""

    decision: Literal[
        "APPROVED", "REJECTED", "MANUAL_REVIEW", "APPROVED_PENDING_REVIEW"
    ] = Field(description="Final decision")
    irs_score: int = Field(
        description="Internal Risk Score (0-100)", ge=0, le=100)
    confidence: float = Field(
        description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Risk level"
    )
    suggested_amount: Optional[float] = Field(
        default=None, description="Suggested loan amount if different"
    )
    suggested_term: Optional[int] = Field(
        default=None, description="Suggested term if different"
    )
    flags: list[str] = Field(description="Risk flags and warnings")
    irs_breakdown: IRSBreakdown = Field(description="Score breakdown")
    osint_validation: Optional[OSINTValidation] = Field(
        default=None, description="OSINT validation results"
    )
    reasoning: str = Field(description="Detailed reasoning for decision")


class AuditTrail(BaseModel):
    """Execution audit trail."""

    triage_passed: bool
    documents_processed: int
    agents_executed: list[str]
    total_llm_calls: int
    total_tool_calls: int


class AnalysisResponse(BaseModel):
    """Complete analysis response."""

    status: Literal["completed", "failed", "timeout"] = Field(
        description="Execution status")
    execution_time_ms: int = Field(
        description="Total execution time in milliseconds")
    case_id: str
    result: Optional[AnalysisResult] = Field(
        default=None, description="Analysis result (null if failed)"
    )
    audit_trail: AuditTrail
    error: Optional[str] = Field(
        default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: str = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict] = Field(
        default=None, description="Additional error details")
    trace_id: Optional[str] = Field(
        default=None, description="Trace ID for debugging")
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(
        description="Health status")
    timestamp: datetime = Field(default_factory=datetime.now)
    database: bool = Field(description="Database connectivity")
    version: str = Field(description="Application version")
