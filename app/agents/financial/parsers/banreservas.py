"""
Bank statement parser for Banreservas.

Extracts transaction data from Banreservas bank statements using GPT-4o-mini OCR.
"""

from app.agents.financial.parsers.bhd import (
    BankStatementData,
    extract_document_data,
    _calculate_summary,
)


# Extraction prompt for Banreservas bank statements
BANRESERVAS_EXTRACTION_PROMPT = """
You are a bank statement parser for Banco de Reservas (Banreservas) - Dominican Republic.

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


async def parse_banreservas_statement(pdf_path: str) -> BankStatementData:
    """
    Parse Banreservas bank statement.

    Automatically detects CSV files and uses fast CSV parsing when available.
    Falls back to PDF OCR if no CSV file is found.

    Args:
        pdf_path: Path to Banreservas bank statement (PDF or CSV)

    Returns:
        Structured bank statement data

    Raises:
        ValueError: If parsing fails or data is invalid

    Examples:
        >>> data = await parse_banreservas_statement("/path/to/banreservas_statement.pdf")
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
        from app.agents.financial.parsers.csv_parser import parse_banreservas_csv
        return parse_banreservas_csv(str(csv_path))

    # Fall back to PDF OCR
    print(f"📄 No CSV found, using PDF OCR: {file_path.name}")

    # Extract data using OCR
    statement_data = await extract_document_data(
        pdf_path=pdf_path,
        extraction_prompt=BANRESERVAS_EXTRACTION_PROMPT,
        response_schema=BankStatementData,
    )

    # Post-process: Ensure bank name is set
    statement_data.bank_name = "Banreservas"

    # Calculate summary if not provided by LLM
    if not statement_data.summary.total_credits:
        statement_data.summary = _calculate_summary(
            statement_data.transactions)

    return statement_data
