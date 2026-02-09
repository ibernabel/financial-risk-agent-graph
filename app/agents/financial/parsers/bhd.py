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

    txn_date: date = Field(description="Transaction date")
    description: str = Field(description="Transaction description")
    amount: Decimal = Field(description="Transaction amount")
    transaction_type: Literal["CREDIT", "DEBIT"] = Field(
        description="Transaction type")
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
    payroll_day: int | None = Field(
        default=None, description="Detected payroll day (1-31)"
    )


class BankStatementData(BaseModel):
    """Structured bank statement data."""

    account_number: str = Field(description="Account number (masked)")
    period_start: date = Field(description="Statement period start date")
    period_end: date = Field(description="Statement period end date")
    transactions: list[Transaction] = Field(description="All transactions")
    summary: TransactionSummary = Field(description="Summary statistics")
    confidence: float = Field(
        default=0.95, description="Parsing confidence score (0.0-1.0)", ge=0.0, le=1.0)


# Extraction prompt for BHD bank statements
BHD_EXTRACTION_PROMPT = """
You are a bank statement parser for Banco BHD (Dominican Republic).

Extract ALL transactions from this bank statement PDF.

**Required Information:**
1. Account number (mask all but last 4 digits, e.g., "****1234")
2. Statement period start and end dates (YYYY-MM-DD format)
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

    Automatically detects CSV files and uses fast CSV parsing when available.
    Falls back to PDF OCR if no CSV file is found.

    Args:
        pdf_path: Path to BHD bank statement (PDF or CSV)

    Returns:
        Structured bank statement data

    Raises:
        ValueError: If parsing fails or data is invalid

    Examples:
        >>> data = await parse_bhd_statement("/path/to/bhd_statement.pdf")
        >>> print(f"Account: {data.account_number}")
        >>> print(f"Transactions: {len(data.transactions)}")
    """
    from pathlib import Path

    # Check if a CSV file exists in the same location
    file_path = Path(pdf_path)
    csv_path = file_path.with_suffix('.csv')

    # If CSV exists, use fast CSV parsing
    if csv_path.exists():
        print(f"✨ Found CSV file, using fast parsing: {csv_path.name}")
        from app.agents.financial.parsers.csv_parser import parse_bhd_csv
        return parse_bhd_csv(str(csv_path))

    # Fall back to PDF OCR
    print(f"📄 No CSV found, using PDF OCR: {file_path.name}")

    # Extract data using OCR
    statement_data = await extract_document_data(
        pdf_path=pdf_path,
        extraction_prompt=BHD_EXTRACTION_PROMPT,
        response_schema=BankStatementData,
    )

    # Calculate summary if not provided by LLM
    if not statement_data.summary.total_credits:
        statement_data.summary = _calculate_summary(
            statement_data.transactions)

    return statement_data


def _calculate_summary(transactions: list[Transaction]) -> TransactionSummary:
    """Calculate summary statistics from transactions."""
    credits = [t.amount for t in transactions if t.transaction_type == "CREDIT"]
    debits = [abs(t.amount)
              for t in transactions if t.transaction_type == "DEBIT"]
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
        payroll_day=payroll_day,
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
    credits = [t for t in transactions if t.transaction_type == "CREDIT"]

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
        if t.transaction_type == "CREDIT" and any(
            abs(t.amount - salary) / salary <= Decimal("0.10")
            for salary in salary_deposits
        )
    ]

    if not salary_txns:
        return None

    # Count frequency of each day
    day_counts: dict[int, int] = {}
    for txn in salary_txns:
        day = txn.txn_date.day
        day_counts[day] = day_counts.get(day, 0) + 1

    # Return most common day
    if day_counts:
        return max(day_counts, key=day_counts.get)  # type: ignore

    return None
