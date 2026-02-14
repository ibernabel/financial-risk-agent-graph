"""
Narrative generation for IRS scores with multilingual support.

Generates Spanish/English narratives explaining IRS scores with citations.
"""

from typing import Literal
from decimal import Decimal

from app.core.state import AgentState
from .scoring import IRSCalculationResult, DeductionRecord


# Spanish templates
TEMPLATES_ES = {
    "executive_summary_low": (
        "El solicitante {applicant_name} presenta un perfil de riesgo {risk_level} "
        "con un score IRS de {score}/100, generado utilizando el grafo de inteligencia CreditGraph AI. {key_findings}"
    ),
    "executive_summary_medium": (
        "El solicitante {applicant_name} presenta un perfil de riesgo {risk_level} "
        "con un score IRS de {score}/100, generado utilizando el grafo de inteligencia CreditGraph AI. Se identificaron algunas áreas de preocupación. {key_findings}"
    ),
    "executive_summary_high": (
        "El solicitante {applicant_name} presenta un perfil de riesgo {risk_level} "
        "con un score IRS de {score}/100, generado utilizando el grafo de inteligencia CreditGraph AI. Se detectaron múltiples indicadores de riesgo. {key_findings}"
    ),
    "executive_summary_critical": (
        "El solicitante {applicant_name} presenta un perfil de riesgo {risk_level} "
        "con un score IRS de {score}/100, generado utilizando el grafo de inteligencia CreditGraph AI. Se identificaron riesgos significativos que requieren atención. {key_findings}"
    ),
    "score_breakdown_header": "\n## Desglose por Variable\n",
    "score_breakdown_item": "- **Variable {variable_letter} ({variable_name}):** {points}/{max_points} puntos",
    "deductions_header": "\n## Deducciones Aplicadas\n",
    "deduction_item": "• **{rule_name}** ({rule_id}): {evidence} → **-{points} puntos**",
    "no_deductions": "No se aplicaron deducciones. Perfil financiero excelente.",
    "recommendation_approve": (
        "\n## Recomendación\n\n"
        "**APROBAR** - El perfil del solicitante cumple con los criterios de riesgo aceptable. "
        "Score IRS de {score}/100 indica riesgo {risk_level}."
    ),
    "recommendation_review": (
        "\n## Recomendación\n\n"
        "**REVISIÓN MANUAL** - El perfil presenta riesgo {risk_level}. "
        "Se recomienda revisión por analista senior para evaluar factores mitigantes."
    ),
    "recommendation_reject": (
        "\n## Recomendación\n\n"
        "**RECHAZAR** - El perfil presenta riesgo {risk_level} con score IRS de {score}/100. "
        "Múltiples indicadores de riesgo identificados."
    ),
}

# English templates
TEMPLATES_EN = {
    "executive_summary_low": (
        "Applicant {applicant_name} presents a {risk_level} risk profile "
        "with an IRS score of {score}/100, generated using the CreditGraph AI intelligence graph. {key_findings}"
    ),
    "executive_summary_medium": (
        "Applicant {applicant_name} presents a {risk_level} risk profile "
        "with an IRS score of {score}/100, generated using the CreditGraph AI intelligence graph. Some areas of concern identified. {key_findings}"
    ),
    "executive_summary_high": (
        "Applicant {applicant_name} presents a {risk_level} risk profile "
        "with an IRS score of {score}/100, generated using the CreditGraph AI intelligence graph. Multiple risk indicators detected. {key_findings}"
    ),
    "executive_summary_critical": (
        "Applicant {applicant_name} presents a {risk_level} risk profile "
        "with an IRS score of {score}/100, generated using the CreditGraph AI intelligence graph. Significant risks identified requiring attention. {key_findings}"
    ),
    "score_breakdown_header": "\n## Score Breakdown\n",
    "score_breakdown_item": "- **Variable {variable_letter} ({variable_name}):** {points}/{max_points} points",
    "deductions_header": "\n## Deductions Applied\n",
    "deduction_item": "• **{rule_name}** ({rule_id}): {evidence} → **-{points} points**",
    "no_deductions": "No deductions applied. Excellent financial profile.",
    "recommendation_approve": (
        "\n## Recommendation\n\n"
        "**APPROVE** - Applicant's profile meets acceptable risk criteria. "
        "IRS score of {score}/100 indicates {risk_level} risk."
    ),
    "recommendation_review": (
        "\n## Recommendation\n\n"
        "**MANUAL REVIEW** - Profile presents {risk_level} risk. "
        "Senior analyst review recommended to evaluate mitigating factors."
    ),
    "recommendation_reject": (
        "\n## Recommendation\n\n"
        "**REJECT** - Profile presents {risk_level} risk with IRS score of {score}/100. "
        "Multiple risk indicators identified."
    ),
}

# Variable names in Spanish and English
VARIABLE_NAMES_ES = {
    "credit_history": "Historial Crediticio",
    "payment_capacity": "Capacidad de Pago",
    "stability": "Estabilidad",
    "collateral": "Garantía",
    "payment_morality": "Moral de Pago",
}

VARIABLE_NAMES_EN = {
    "credit_history": "Credit History",
    "payment_capacity": "Payment Capacity",
    "stability": "Stability",
    "collateral": "Collateral",
    "payment_morality": "Payment Morality",
}

VARIABLE_LETTERS = {
    "credit_history": "A",
    "payment_capacity": "B",
    "stability": "C",
    "collateral": "D",
    "payment_morality": "E",
}

RISK_LEVEL_ES = {
    "LOW": "BAJO",
    "MEDIUM": "MEDIO",
    "HIGH": "ALTO",
    "CRITICAL": "CRÍTICO",
}

RISK_LEVEL_EN = {
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "CRITICAL",
}


class NarrativeGenerator:
    """Generates multilingual narratives explaining IRS scores."""

    def __init__(self, language: Literal["es", "en"] = "es"):
        """
        Initialize narrative generator.

        Args:
            language: Language for narrative ("es" for Spanish, "en" for English)
        """
        self.language = language
        self.templates = TEMPLATES_ES if language == "es" else TEMPLATES_EN
        self.variable_names = (
            VARIABLE_NAMES_ES if language == "es" else VARIABLE_NAMES_EN
        )
        self.risk_levels = RISK_LEVEL_ES if language == "es" else RISK_LEVEL_EN

    def generate_narrative(
        self, irs_result: IRSCalculationResult, state: AgentState
    ) -> str:
        """
        Generate full narrative with:
        - Executive summary
        - Score breakdown by variable
        - All deductions with evidence
        - Recommendation

        Args:
            irs_result: IRS calculation result
            state: Current agent state

        Returns:
            Complete narrative in selected language
        """
        sections = [
            self._generate_executive_summary(irs_result, state),
            self._generate_score_breakdown(irs_result),
            self._generate_deductions_narrative(irs_result),
            self._generate_recommendation(irs_result),
        ]
        return "\n".join(sections)

    def _generate_executive_summary(
        self, irs_result: IRSCalculationResult, state: AgentState
    ) -> str:
        """Generate opening summary paragraph."""
        applicant_name = state.applicant.get("full_name", "El solicitante")
        risk_level = self.risk_levels[irs_result.risk_level]
        score = irs_result.final_score

        # Select template based on risk level
        template_key = f"executive_summary_{irs_result.risk_level.lower()}"
        template = self.templates[template_key]

        # Generate key findings
        key_findings = self._generate_key_findings(irs_result, state)

        return template.format(
            applicant_name=applicant_name,
            risk_level=risk_level,
            score=score,
            key_findings=key_findings,
        )

    def _generate_key_findings(
        self, irs_result: IRSCalculationResult, state: AgentState
    ) -> str:
        """Generate key findings summary."""
        findings = []

        # Credit score mention
        if state.financial_analysis and state.financial_analysis.credit_score:
            credit_score = state.financial_analysis.credit_score
            if self.language == "es":
                findings.append(f"Score de buró: {credit_score}")
            else:
                findings.append(f"Bureau score: {credit_score}")

        # Major flags
        critical_flags = [
            f for f in irs_result.flags if "INFORMAL_LENDER" in f or "CRITICAL" in f
        ]
        if critical_flags:
            if self.language == "es":
                findings.append("Indicadores críticos detectados")
            else:
                findings.append("Critical indicators detected")

        return ". ".join(findings) if findings else ""

    def _generate_score_breakdown(self, irs_result: IRSCalculationResult) -> str:
        """Generate variable-by-variable breakdown."""
        lines = [self.templates["score_breakdown_header"]]

        for var_name, points in irs_result.breakdown.items():
            from .rules import VARIABLE_WEIGHTS

            max_points = VARIABLE_WEIGHTS[var_name]
            var_letter = VARIABLE_LETTERS[var_name]
            var_display_name = self.variable_names[var_name]

            line = self.templates["score_breakdown_item"].format(
                variable_letter=var_letter,
                variable_name=var_display_name,
                points=points,
                max_points=max_points,
            )
            lines.append(line)

        return "\n".join(lines)

    def _generate_deductions_narrative(self, irs_result: IRSCalculationResult) -> str:
        """Generate detailed explanation of each deduction."""
        if not irs_result.deductions:
            return f"\n{self.templates['no_deductions']}"

        lines = [self.templates["deductions_header"]]

        for deduction in irs_result.deductions:
            line = self.templates["deduction_item"].format(
                rule_name=deduction.rule_name,
                rule_id=deduction.rule_id,
                evidence=deduction.evidence,
                points=deduction.points_deducted,
            )
            lines.append(line)

        return "\n".join(lines)

    def _generate_recommendation(self, irs_result: IRSCalculationResult) -> str:
        """Generate final recommendation paragraph."""
        score = irs_result.final_score
        risk_level = self.risk_levels[irs_result.risk_level]

        # Determine recommendation based on score
        if score >= 85:
            template_key = "recommendation_approve"
        elif score >= 60:
            template_key = "recommendation_review"
        else:
            template_key = "recommendation_reject"

        return self.templates[template_key].format(score=score, risk_level=risk_level)
