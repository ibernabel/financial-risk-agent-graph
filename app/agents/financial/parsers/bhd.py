"""
Bank statement parser for Banco BHD.

Extracts transaction data from BHD bank statements using GPT-4o-mini OCR.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.ocr import extract_document_data


class Transaction(BaseModel):
    """Individual bank transaction."""

    date: date = Field(description="Transaction date")
    description: str = Field(description="Transaction description")
    amount: Decimal = Field(description="Transaction amount")
    type: Literal["CREDIT", "DEBIT"] = Field(description="Transaction type")
    balance: Decimal = Field(description="Account balance after transaction")
    category: Literal["SALARY", "TRANSFER", "PAYMENT", "OTHER"] = Field(
        default="OTHER", description="Transaction category"
    )


class DateRange(BaseModel):
    """Date range for statement period."""

    start_date: date = Field(description="Period start date")
    end_date: date = Field(description="Period end date")


class TransactionSummary(BaseModel):
    """Summary statistics for bank statement."""

    total_credits: Decimal = Field(description="Total credits in period")
    total_debits: Decimal = Field(description="Total debits in period")
    average_balance: Decimal = Field(description="Average account balance")
    salary_deposits: list[Decimal] = Field(
        default_factory=list, description="Detected salary deposits"
    )
    detected_payroll_day: int | None = Field(
        default=None, description="Detected payroll day (1-31)"
    )


class BankStatementData(BaseModel):
    """Structured bank statement data."""

    bank_name: str = Field(description="Bank name")
    account_number: str = Field(description="Account number (masked)")
    period: DateRange = Field(description="Statement period")
    transactions: list[Transaction] = Field(description="All transactions")
    summary: TransactionSummary = Field(description="Summary statistics")


# Extraction prompt for BHD bank statements
BHD_EXTRACTION_PROMPT = """
You are a bank statement parser for Banco BHD (Dominican Republic).

Extract ALL transactions from this bank statement PDF.

**Required Information:**
1. Account number (mask all but last 4 digits, e.g., "****1234")
2. Statement period (start and end dates)
3. All transactions with:
   - Date (YYYY-MM-DD format)
   - Description (as shown on statement)
   - Amount (positive for credits, negative for debits)
   - Type (CREDIT or DEBIT)
   - Balance after transaction

**Important:**
- Extract EVERY transaction, do not skip any
- Preserve exact descriptions from the statement
- Use negative amounts for debits
- Account number must be masked (show only last 4 digits)

**Output Format:**
Return structured JSON matching the BankStatementData schema.
"""


async def parse_bhd_statement(pdf_path: str) -> BankStatementData:
    """
    Parse Banco BHD bank statement.

    Args:
        pdf_path: Path to BHD bank statement PDF

    Returns:
        Structured bank statement data

    Raises:
        ValueError: If parsing fails or data is invalid

    Examples:
        >>> data = await parse_bhd_statement("/path/to/bhd_statement.pdf")
        >>> print(f"Account: {data.account_number}")
        >>> print(f"Transactions: {len(data.transactions)}")
    """
    # Extract data using OCR
    statement_data = await extract_document_data(
        pdf_path=pdf_path,
        extraction_prompt=BHD_EXTRACTION_PROMPT,
        response_schema=BankStatementData,
    )

    # Post-process: Ensure bank name is set
    statement_data.bank_name = "Banco BHD"

    # Calculate summary if not provided by LLM
    if not statement_data.summary.total_credits:
        statement_data.summary = _calculate_summary(
            statement_data.transactions)

    return statement_data


def _calculate_summary(transactions: list[Transaction]) -> TransactionSummary:
    """Calculate summary statistics from transactions."""
    credits = [t.amount for t in transactions if t.type == "CREDIT"]
    debits = [abs(t.amount) for t in transactions if t.type == "DEBIT"]
    balances = [t.balance for t in transactions]

    total_credits = sum(credits, Decimal("0"))
    total_debits = sum(debits, Decimal("0"))
    average_balance = sum(balances, Decimal("0")) / \
        len(balances) if balances else Decimal("0")

    # Detect salary deposits (recurring credits with similar amounts)
    salary_deposits = _detect_salary_deposits(transactions)

    # Detect payroll day
    payroll_day = _detect_payroll_day(salary_deposits, transactions)

    return TransactionSummary(
        total_credits=total_credits,
        total_debits=total_debits,
        average_balance=average_balance,
        salary_deposits=salary_deposits,
        detected_payroll_day=payroll_day,
    )


def _detect_salary_deposits(transactions: list[Transaction]) -> list[Decimal]:
    """
    Detect recurring salary deposits.

    Logic:
    1. Filter credits
    2. Group by amount similarity (±10% variance)
    3. Check for monthly recurrence
    4. Return amounts classified as salary
    """
    credits = [t for t in transactions if t.type == "CREDIT"]

    if not credits:
        return []

    # Group similar amounts (±10% variance)
    salary_candidates: dict[Decimal, list[Transaction]] = {}

    for credit in credits:
        amount = credit.amount
        matched = False

        for key in salary_candidates:
            variance = abs(amount - key) / key if key > 0 else Decimal("1")
            if variance <= Decimal("0.10"):  # 10% tolerance
                salary_candidates[key].append(credit)
                matched = True
                break

        if not matched:
            salary_candidates[amount] = [credit]

    # Find recurring deposits (at least 2 occurrences)
    salary_amounts = []
    for amount, txns in salary_candidates.items():
        if len(txns) >= 2:
            salary_amounts.append(amount)

    return salary_amounts


def _detect_payroll_day(
    salary_deposits: list[Decimal], transactions: list[Transaction]
) -> int | None:
    """
    Detect payroll day from salary deposits.

    Returns the most common day of month for salary deposits.
    """
    if not salary_deposits:
        return None

    # Find transactions matching salary amounts
    salary_txns = [
        t for t in transactions
        if t.type == "CREDIT" and any(
            abs(t.amount - salary) / salary <= Decimal("0.10")
            for salary in salary_deposits
        )
    ]

    if not salary_txns:
        return None

    # Count frequency of each day
    day_counts: dict[int, int] = {}
    for txn in salary_txns:
        day = txn.date.day
        day_counts[day] = day_counts.get(day, 0) + 1

    # Return most common day
    if day_counts:
        return max(day_counts, key=day_counts.get)  # type: ignore

    return None
