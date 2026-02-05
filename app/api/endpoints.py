"""
FastAPI endpoints for CreditFlow AI.

Provides REST API for credit risk analysis.
"""

import time
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResult,
    AuditTrail,
    ErrorResponse,
    HealthResponse,
    IRSBreakdown,
    OSINTValidation,
)
from app.core.config import settings
from app.core.state import AgentState
from app.core.graph import get_compiled_graph
from app.core.database import db


# Create API router
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status with database connectivity
    """
    db_healthy = await db.health_check()

    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        timestamp=datetime.now(),
        database=db_healthy,
        version=settings.api.version,
    )


@router.post(
    "/api/v1/analysis/execute",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
)
async def execute_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """
    Execute credit risk analysis.

    Orchestrates all agents to analyze the applicant and return a decision.

    Args:
        request: Analysis request with applicant, loan, and document data

    Returns:
        Analysis response with decision and audit trail

    Raises:
        HTTPException: On validation or execution errors
    """
    start_time = time.time()
    trace_id = str(uuid.uuid4())

    try:
        # Initialize agent state from request
        initial_state = AgentState(
            case_id=request.case_id,
            applicant=request.applicant.model_dump(),
            loan=request.loan.model_dump(),
            documents=[doc.model_dump() for doc in request.documents],
            config=request.config.model_dump(),
            current_step="initialized",
            messages=[],
            agents_executed=[],
            llm_calls=0,
            tool_calls=0,
            errors=[],
            execution_time_ms=0,
        )

        # Get compiled graph
        graph = await get_compiled_graph()

        # Execute graph
        config = {
            "configurable": {
                "thread_id": request.case_id,
                "checkpoint_ns": "creditflow",
            }
        }

        # Run the graph
        final_state = await graph.ainvoke(initial_state, config=config)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Build response from final state
        if final_state.final_decision:
            # Build IRS breakdown
            irs_breakdown = None
            if final_state.irs_score:
                irs_breakdown = IRSBreakdown(**final_state.irs_score.breakdown)

            # Build OSINT validation
            osint_validation = None
            if final_state.osint_findings:
                osint_validation = OSINTValidation(
                    business_found=final_state.osint_findings.business_found,
                    digital_veracity_score=final_state.osint_findings.digital_veracity_score,
                    sources_checked=final_state.osint_findings.sources_checked,
                )

            # Build analysis result
            result = AnalysisResult(
                decision=final_state.final_decision.decision,
                irs_score=final_state.irs_score.score if final_state.irs_score else 0,
                confidence=final_state.final_decision.confidence,
                risk_level=final_state.final_decision.risk_level,
                suggested_amount=final_state.final_decision.suggested_amount,
                suggested_term=final_state.final_decision.suggested_term,
                flags=final_state.irs_score.flags if final_state.irs_score else [],
                irs_breakdown=irs_breakdown or IRSBreakdown(
                    credit_history=0,
                    payment_capacity=0,
                    stability=0,
                    collateral=0,
                    payment_morality=0,
                ),
                osint_validation=osint_validation,
                reasoning=final_state.final_decision.reasoning,
            )

            # Build audit trail
            audit_trail = AuditTrail(
                triage_passed=(
                    final_state.triage_result.status == "PASSED"
                    if final_state.triage_result
                    else False
                ),
                documents_processed=len(final_state.documents_processed),
                agents_executed=final_state.agents_executed,
                total_llm_calls=final_state.llm_calls,
                total_tool_calls=final_state.tool_calls,
            )

            return AnalysisResponse(
                status="completed",
                execution_time_ms=execution_time_ms,
                case_id=request.case_id,
                result=result,
                audit_trail=audit_trail,
                error=None,
                timestamp=datetime.now(),
            )
        else:
            # No decision was made (shouldn't happen in normal flow)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Analysis completed but no decision was generated",
            )

    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Error executing analysis: {str(e)}")

        # Return error response
        execution_time_ms = int((time.time() - start_time) * 1000)

        return AnalysisResponse(
            status="failed",
            execution_time_ms=execution_time_ms,
            case_id=request.case_id,
            result=None,
            audit_trail=AuditTrail(
                triage_passed=False,
                documents_processed=0,
                agents_executed=[],
                total_llm_calls=0,
                total_tool_calls=0,
            ),
            error=str(e),
            timestamp=datetime.now(),
        )
