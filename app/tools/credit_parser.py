"""
Credit Report Parser API client.

Integrates with TransUnion Credit Report Parser service for credit data extraction.
"""

import httpx
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal

from app.core.config import settings


class Inquirer(BaseModel):
    """Credit report inquirer information."""

    suscriptor: str = Field(description="Subscriber name")
    usuario: str = Field(description="User name")
    fecha_consulta: str = Field(description="Query date")
    hora_consulta: str = Field(description="Query time")


class PhoneNumbers(BaseModel):
    """Phone numbers from credit report."""

    casa: str = Field(default="", description="Home phone")
    trabajo: str = Field(default="", description="Work phone")
    celular: str = Field(default="", description="Mobile phone")


class PersonalData(BaseModel):
    """Personal information from credit report."""

    cedula: str = Field(description="National ID (masked)")
    nombres: str = Field(description="First names (masked)")
    apellidos: str = Field(description="Last names (masked)")
    fecha_nacimiento: str = Field(description="Date of birth (DD/MM/YYYY)")
    edad: int = Field(description="Age")
    ocupacion: str = Field(default="", description="Occupation")
    lugar_nacimiento: str = Field(default="", description="Place of birth")
    pasaporte: Optional[str] = Field(
        default=None, description="Passport number")
    estado_civil: str = Field(default="", description="Marital status")
    phones: PhoneNumbers = Field(description="Phone numbers")
    direcciones: list[str] = Field(
        default_factory=list, description="Addresses (masked)")


class CreditScore(BaseModel):
    """Credit score information."""

    score: int = Field(ge=300, le=850, description="Credit score (300-850)")
    factors: list[str] = Field(
        default_factory=list, description="Score factors")


class SummaryOpenAccount(BaseModel):
    """Summary of open credit account."""

    subscriber: str = Field(description="Financial institution name")
    accounts_amount: int = Field(description="Number of accounts")
    account_type: str = Field(
        description="Account type (TC=credit card, PR=loan, etc)")
    credit_amount_dop: float = Field(description="Credit limit in DOP")
    credit_amount_usd: float = Field(description="Credit limit in USD")
    current_balance_dop: float = Field(description="Current balance in DOP")
    current_balance_usd: float = Field(description="Current balance in USD")
    current_overdue_dop: float = Field(description="Overdue amount in DOP")
    current_overdue_usd: float = Field(description="Overdue amount in USD")
    utilization_percent_dop: float = Field(
        description="Credit utilization % in DOP")
    utilization_percent_usd: float = Field(
        description="Credit utilization % in USD")


class CreditReport(BaseModel):
    """Complete credit report data from TransUnion API."""

    inquirer: Inquirer = Field(description="Report inquirer information")
    personal_data: PersonalData = Field(description="Personal data")
    score: CreditScore = Field(description="Credit score and factors")
    summary_open_accounts: list[SummaryOpenAccount] = Field(
        default_factory=list, description="Summary of open accounts"
    )


class CreditParserClient:
    """Client for TransUnion Credit Report Parser API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_url = api_url or settings.external.credit_parser_url
        self.api_key = api_key or settings.external.credit_parser_api_key
        self.timeout = timeout

    async def parse_credit_report(self, pdf_path: str) -> CreditReport:
        """
        Parse a credit report PDF using the TransUnion API.

        Args:
            pdf_path: Path to the credit report PDF file

        Returns:
            Parsed CreditReport object

        Raises:
            httpx.HTTPError: If the API request fails
            ValueError: If the response cannot be parsed
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare file upload
            with open(pdf_path, "rb") as f:
                files = {"file": (Path(pdf_path).name, f, "application/pdf")}
                headers = {"X-API-Key": self.api_key}

                # Make request to /v1/parse endpoint (API uses /v1 prefix)
                response = await client.post(
                    f"{self.api_url}/v1/parse",
                    files=files,
                    headers=headers,
                )
                response.raise_for_status()

            # Parse response
            data = response.json()

            # Convert to CreditReport model
            # Note: Field mapping may need adjustment based on actual API response
            return self._map_response_to_model(data)

    def _map_response_to_model(self, data: dict) -> CreditReport:
        """
        Map API response to CreditReport model.

        The TransUnion API returns data with Spanish field names.
        Pydantic handles validation and type conversion automatically.

        Args:
            data: Raw API response dictionary

        Returns:
            CreditReport instance
        """
        return CreditReport(**data)

    async def health_check(self) -> bool:
        """
        Check if Credit Parser API is available.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Assuming health endpoint at /health
                health_url = self.api_url.replace("/v1/parse", "/health")
                response = await client.get(health_url)
                return response.status_code == 200
        except Exception:
            return False


# Global client instance
credit_parser_client = CreditParserClient()
