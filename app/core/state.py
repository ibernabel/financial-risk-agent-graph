"""
State management for LangGraph using Pydantic models.

Defines the shared state schema and nested models for agent communication.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class TriageResult(BaseModel):
    """Result from the Triage Agent."""

    status: str = Field(description="PASSED or REJECTED")
    rejection_reason: Optional[str] = Field(
        default=None, description="Reason for rejection")
    eligibility_flags: list[str] = Field(
        default_factory=list, description="Eligibility warning flags"
    )


class FinancialAnalysis(BaseModel):
    """Result from the Financial Analyst Agent."""

    total_credits: float = Field(description="Total credits in period")
    total_debits: float = Field(description="Total debits in period")
    average_balance: float = Field(description="Average account balance")
    salary_deposits: list[float] = Field(
        default_factory=list, description="Detected salary deposits"
    )
    detected_payroll_day: Optional[int] = Field(
        default=None, description="Detected payroll day (1-31)"
    )
    detected_patterns: list[str] = Field(
        default_factory=list, description="Risk patterns detected (FIN-01, FIN-02, etc.)"
    )


class OSINTFindings(BaseModel):
    """Result from the OSINT Researcher Agent."""

    business_found: bool = Field(
        description="Whether business was found online")
    digital_veracity_score: float = Field(
        description="Digital Veracity Score (0.0-1.0)", ge=0.0, le=1.0
    )
    sources_checked: list[str] = Field(
        default_factory=list, description="Platforms searched (google_maps, instagram, etc.)"
    )
    evidence: dict = Field(
        default_factory=dict, description="Evidence found per platform"
    )


class IRSScore(BaseModel):
    """Result from the IRS Engine."""

    score: int = Field(description="Internal Risk Score (0-100)", ge=0, le=100)
    breakdown: dict[str, int] = Field(
        description="Score breakdown by variable (credit_history, payment_capacity, etc.)"
    )
    flags: list[str] = Field(default_factory=list, description="Risk flags")
    deductions: list[dict] = Field(
        default_factory=list, description="Deductions applied with justification"
    )
    narrative: str = Field(
        default="", description="Narrative explanation of score")


class FinalDecision(BaseModel):
    """Result from the Underwriter Agent."""

    decision: str = Field(
        description="APPROVED, REJECTED, MANUAL_REVIEW, or APPROVED_PENDING_REVIEW"
    )
    confidence: float = Field(
        description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    risk_level: str = Field(description="LOW, MEDIUM, HIGH, or CRITICAL")
    suggested_amount: Optional[float] = Field(
        default=None, description="Suggested loan amount if different from requested"
    )
    suggested_term: Optional[int] = Field(
        default=None, description="Suggested term in months if different from requested"
    )
    reasoning: str = Field(description="Detailed reasoning for decision")
    requires_human_review: bool = Field(
        default=False, description="Whether human review is required"
    )


class AgentState(BaseModel):
    """
    Shared state for the LangGraph workflow.

    This state is passed between all agents and updated as the workflow progresses.
    Uses Pydantic for automatic validation and serialization.
    """

    # Input fields (from API request)
    case_id: str = Field(description="Unique case identifier")
    applicant: dict = Field(description="Applicant personal information")
    loan: dict = Field(description="Loan request details")
    documents: list[dict] = Field(description="Uploaded documents")
    config: dict = Field(default_factory=dict,
                         description="Request configuration")

    # Execution tracking
    current_step: str = Field(default="initialized",
                              description="Current workflow step")
    messages: list[BaseMessage] = Field(
        default_factory=list, description="LLM message history"
    )

    # Agent outputs (populated as agents execute)
    triage_result: Optional[TriageResult] = Field(
        default=None, description="Triage agent result"
    )
    documents_processed: list[dict] = Field(
        default_factory=list, description="Processed document metadata"
    )
    financial_analysis: Optional[FinancialAnalysis] = Field(
        default=None, description="Financial analyst result"
    )
    osint_findings: Optional[OSINTFindings] = Field(
        default=None, description="OSINT researcher result"
    )
    irs_score: Optional[IRSScore] = Field(
        default=None, description="IRS engine result")
    final_decision: Optional[FinalDecision] = Field(
        default=None, description="Underwriter decision"
    )

    # Audit trail
    agents_executed: list[str] = Field(
        default_factory=list, description="List of agents that have executed"
    )
    llm_calls: int = Field(default=0, description="Total LLM API calls made")
    tool_calls: int = Field(default=0, description="Total tool calls made")
    errors: list[dict] = Field(
        default_factory=list, description="Errors encountered")
    execution_time_ms: int = Field(
        default=0, description="Total execution time in milliseconds")

    model_config = {
        "arbitrary_types_allowed": True,  # Allow BaseMessage type
        "json_schema_extra": {
            "example": {
                "case_id": "REQ-2026-001",
                "applicant": {
                    "id": "001-XXXXXXX-X",
                    "full_name": "Juan Pérez",
                    "date_of_birth": "1988-12-30",
                    "declared_salary": 35000.0,
                },
                "loan": {
                    "requested_amount": 75000.0,
                    "term_months": 24,
                    "product_type": "PERSONAL_LOAN",
                },
                "documents": [],
                "current_step": "initialized",
            }
        },
    }
