"""
Narrative generator for the Underwriter Agent.

Generates detailed reasoning narratives in Spanish and English.
Explains the final decision with evidence from all agents.
"""

from decimal import Decimal
from typing import Literal
from app.core.state import AgentState


# ============================================================================
# Narrative Templates
# ============================================================================

NARRATIVES_ES = {
    "decision_header": {
        "APPROVED": "✅ **APROBADO**",
        "REJECTED": "❌ **RECHAZADO**",
        "MANUAL_REVIEW": "📋 **REVISIÓN MANUAL REQUERIDA**",
        "APPROVED_PENDING_REVIEW": "⚠️ **APROBADO PENDIENTE DE REVISIÓN**",
    },
    "risk_level": {
        "LOW": "BAJO",
        "MEDIUM": "MEDIO",
        "HIGH": "ALTO",
        "CRITICAL": "CRÍTICO",
    },
}

NARRATIVES_EN = {
    "decision_header": {
        "APPROVED": "✅ **APPROVED**",
        "REJECTED": "❌ **REJECTED**",
        "MANUAL_REVIEW": "📋 **MANUAL REVIEW REQUIRED**",
        "APPROVED_PENDING_REVIEW": "⚠️ **APPROVED PENDING REVIEW**",
    },
    "risk_level": {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL",
    },
}


# ============================================================================
# Narrative Generation
# ============================================================================


def generate_narrative(
    state: AgentState,
    decision: str,
    risk_level: str,
    confidence: float,
    suggested_amount: Decimal | None,
    suggested_term: int | None,
    language: Literal["es", "en"] = "es",
) -> str:
    """
    Generate detailed reasoning narrative for the final decision.

    Structure:
    1. Decision header with IRS score and risk level
    2. Key findings from each agent
    3. Confidence score with factors
    4. Recommendation

    Args:
        state: Current agent state
        decision: Final decision
        risk_level: Risk level (LOW/MEDIUM/HIGH/CRITICAL)
        confidence: Confidence score (0.0-1.0)
        suggested_amount: Suggested amount (if any)
        suggested_term: Suggested term (if any)
        language: Narrative language (es or en)

    Returns:
        Formatted narrative string
    """
    if language == "es":
        return _generate_narrative_es(
            state, decision, risk_level, confidence, suggested_amount, suggested_term
        )
    else:
        return _generate_narrative_en(
            state, decision, risk_level, confidence, suggested_amount, suggested_term
        )


def _generate_narrative_es(
    state: AgentState,
    decision: str,
    risk_level: str,
    confidence: float,
    suggested_amount: Decimal | None,
    suggested_term: int | None,
) -> str:
    """Generate Spanish narrative."""
    parts = []

    # Header
    decision_header = NARRATIVES_ES["decision_header"][decision]
    risk_label = NARRATIVES_ES["risk_level"][risk_level]
    irs_score = state.irs_score.score if state.irs_score else 0

    parts.append(f"{decision_header}\n")
    parts.append(
        f"**IRS Score:** {irs_score}/100 (Nivel de Riesgo: {risk_label})\n")
    parts.append(f"**Confianza:** {confidence:.1%}\n\n")

    # Key findings
    parts.append("## Hallazgos Clave\n\n")

    # 1. Credit History (from IRS narrative summary)
    if state.irs_score and state.irs_score.narrative:
        # Extract first sentence from IRS narrative
        irs_summary = state.irs_score.narrative.split(".")[0] + "."
        parts.append(f"**Historial Crediticio:** {irs_summary}\n\n")

    # 2. Financial Analysis
    if state.financial_analysis:
        fa = state.financial_analysis
        if fa.detected_salary_amount:
            parts.append(
                f"**Salario Detectado:** RD${fa.detected_salary_amount:,.2f}/mes\n")
        if fa.credit_score:
            parts.append(f"**Score de Buró:** {fa.credit_score}\n")
        if fa.risk_flags:
            parts.append(
                f"**Banderas de Riesgo:** {', '.join(fa.risk_flags)}\n")
        parts.append("\n")

    # 3. OSINT Validation
    if state.osint_findings and not state.config.get("skip_osint", False):
        osint = state.osint_findings
        if osint.business_found:
            parts.append(
                f"**Validación OSINT:** Negocio encontrado con score de veracidad {osint.digital_veracity_score:.1%}\n"
            )
        else:
            parts.append(
                "**Validación OSINT:** Negocio no encontrado en línea\n")
        parts.append("\n")

    # 4. Suggested Amount/Term
    if suggested_amount:
        parts.append(
            f"**Monto Sugerido:** RD${suggested_amount:,.2f} (reducido por capacidad de pago)\n\n")

    # Recommendation
    parts.append("## Recomendación\n\n")

    if decision == "APPROVED":
        parts.append(
            f"El solicitante presenta un perfil de riesgo {risk_label} con IRS de {irs_score} puntos. "
            f"Se recomienda **APROBAR** el préstamo según los términos solicitados. "
            f"Confianza del análisis: {confidence:.1%}."
        )
    elif decision == "APPROVED_PENDING_REVIEW":
        parts.append(
            f"El solicitante califica con IRS de {irs_score} puntos, pero la confianza del análisis es {confidence:.1%} "
            f"(por debajo del umbral de 85%). Se recomienda **APROBAR** con revisión manual para verificar los datos."
        )
    elif decision == "MANUAL_REVIEW":
        if suggested_amount:
            parts.append(
                f"El solicitante presenta un perfil de riesgo {risk_label} con IRS de {irs_score} puntos. "
                f"Se recomienda **REVISIÓN MANUAL** y considerar un monto reducido de RD${suggested_amount:,.2f} "
                f"para alinear con la capacidad de pago."
            )
        else:
            parts.append(
                f"El solicitante presenta un perfil de riesgo {risk_label} con IRS de {irs_score} puntos. "
                f"Se requiere **REVISIÓN MANUAL** por analista senior antes de tomar una decisión final."
            )
    else:  # REJECTED
        parts.append(
            f"El solicitante presenta un perfil de riesgo {risk_label} con IRS de {irs_score} puntos "
            f"(por debajo del umbral mínimo de 60). Se recomienda **RECHAZAR** el préstamo debido a los riesgos identificados."
        )

    return "".join(parts)


def _generate_narrative_en(
    state: AgentState,
    decision: str,
    risk_level: str,
    confidence: float,
    suggested_amount: Decimal | None,
    suggested_term: int | None,
) -> str:
    """Generate English narrative."""
    parts = []

    # Header
    decision_header = NARRATIVES_EN["decision_header"][decision]
    risk_label = NARRATIVES_EN["risk_level"][risk_level]
    irs_score = state.irs_score.score if state.irs_score else 0

    parts.append(f"{decision_header}\n")
    parts.append(
        f"**IRS Score:** {irs_score}/100 (Risk Level: {risk_label})\n")
    parts.append(f"**Confidence:** {confidence:.1%}\n\n")

    # Key findings
    parts.append("## Key Findings\n\n")

    # 1. Credit History
    if state.irs_score and state.irs_score.narrative:
        irs_summary = state.irs_score.narrative.split(".")[0] + "."
        parts.append(f"**Credit History:** {irs_summary}\n\n")

    # 2. Financial Analysis
    if state.financial_analysis:
        fa = state.financial_analysis
        if fa.detected_salary_amount:
            parts.append(
                f"**Detected Salary:** DOP {fa.detected_salary_amount:,.2f}/month\n")
        if fa.credit_score:
            parts.append(f"**Bureau Score:** {fa.credit_score}\n")
        if fa.risk_flags:
            parts.append(f"**Risk Flags:** {', '.join(fa.risk_flags)}\n")
        parts.append("\n")

    # 3. OSINT Validation
    if state.osint_findings and not state.config.get("skip_osint", False):
        osint = state.osint_findings
        if osint.business_found:
            parts.append(
                f"**OSINT Validation:** Business found with {osint.digital_veracity_score:.1%} veracity score\n"
            )
        else:
            parts.append("**OSINT Validation:** Business not found online\n")
        parts.append("\n")

    # 4. Suggested Amount/Term
    if suggested_amount:
        parts.append(
            f"**Suggested Amount:** DOP {suggested_amount:,.2f} (reduced per payment capacity)\n\n")

    # Recommendation
    parts.append("## Recommendation\n\n")

    if decision == "APPROVED":
        parts.append(
            f"Applicant presents a {risk_label} risk profile with IRS score of {irs_score}. "
            f"Recommend to **APPROVE** loan per requested terms. "
            f"Analysis confidence: {confidence:.1%}."
        )
    elif decision == "APPROVED_PENDING_REVIEW":
        parts.append(
            f"Applicant qualifies with IRS score of {irs_score}, but analysis confidence is {confidence:.1%} "
            f"(below 85% threshold). Recommend to **APPROVE** with manual review to verify data."
        )
    elif decision == "MANUAL_REVIEW":
        if suggested_amount:
            parts.append(
                f"Applicant presents a {risk_label} risk profile with IRS score of {irs_score}. "
                f"Recommend **MANUAL REVIEW** and consider reduced amount of DOP {suggested_amount:,.2f} "
                f"aligned with payment capacity."
            )
        else:
            parts.append(
                f"Applicant presents a {risk_label} risk profile with IRS score of {irs_score}. "
                f"**MANUAL REVIEW** required by senior analyst before final decision."
            )
    else:  # REJECTED
        parts.append(
            f"Applicant presents a {risk_label} risk profile with IRS score of {irs_score} "
            f"(below minimum threshold of 60). Recommend to **REJECT** loan due to identified risks."
        )

    return "".join(parts)
