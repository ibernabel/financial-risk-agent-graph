"""
CSV parser utilities for bank statements.

Provides fast, direct parsing of CSV bank statements without OCR.
"""

import csv
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from app.agents.financial.parsers.bhd import (
    BankStatementData,
    Transaction,
    TransactionSummary,
)


def parse_bhd_csv(csv_path: str) -> BankStatementData:
    """
    Parse BHD bank statement from CSV format.

    CSV Format (semicolon-delimited):
    Row 1: Empty/header
    Row 2: Headers (Fecha, Número de Referencia, Descripción, Débitos, Créditos, Balance)
    Row 3+: Transaction data

    Args:
        csv_path: Path to BHD CSV file

    Returns:
        Structured bank statement data
    """
    transactions = []

    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Read all lines and filter out empty ones
        lines = [line.strip() for line in f if line.strip()]

        # Skip first two rows (empty and headers)
        data_lines = lines[2:]

        for line in data_lines:
            # Split by semicolon
            fields = line.split(';')

            # Filter out empty fields and extract data
            # Format: ;Fecha;Ref;;Descripción;Débitos;Créditos;Balance;;
            if len(fields) >= 8:
                fecha = fields[1].strip()
                descripcion = fields[4].strip()
                debito = fields[5].strip()
                credito = fields[6].strip()
                balance = fields[7].strip()

                if fecha and descripcion:
                    # Parse date (DD-MM-YYYY format)
                    try:
                        txn_date = datetime.strptime(fecha, '%d-%m-%Y').date()
                    except ValueError:
                        continue

                    # Determine transaction type and amount
                    if credito and credito != '0':
                        tx_type = "CREDIT"
                        amount = Decimal(credito.replace(',', ''))
                    else:
                        tx_type = "DEBIT"
                        amount = Decimal(debito.replace(
                            ',', '')) if debito and debito != '0' else Decimal('0')

                    # Parse balance
                    balance_decimal = Decimal(balance.replace(
                        ',', '')) if balance else Decimal('0')

                    # Create transaction
                    transaction = Transaction(
                        txn_date=txn_date,
                        description=descripcion,
                        amount=amount,
                        transaction_type=tx_type,
                        balance=balance_decimal,
                        category="OTHER"
                    )
                    transactions.append(transaction)

    if not transactions:
        raise ValueError("No transactions found in CSV file")

    # Extract account number (mask it for privacy)
    account_number = "****CSV"

    # Determine period from transaction dates
    period_start = min(t.txn_date for t in transactions)
    period_end = max(t.txn_date for t in transactions)

    # Calculate summary
    summary = _calculate_summary_from_transactions(transactions)

    return BankStatementData(
        account_number=account_number,
        period_start=period_start,
        period_end=period_end,
        transactions=transactions,
        summary=summary,
        confidence=1.0  # CSV parsing is 100% accurate
    )


def parse_popular_csv(csv_path: str) -> BankStatementData:
    """
    Parse Banco Popular statement from CSV format.

    CSV Format:
    - Header rows with account info
    - Transaction data in subsequent rows

    Args:
        csv_path: Path to Popular CSV file

    Returns:
        Structured bank statement data
    """
    transactions = []
    account_number = "****CSV"

    with open(csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        lines = f.readlines()

        # Extract account number from header
        for line in lines[:10]:
            if 'Cuenta:' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    account_full = parts[1].strip()
                    # Mask all but last 4 digits
                    if len(account_full) >= 4:
                        account_number = f"****{account_full[-4:]}"
                break

        # Find where transaction data starts
        data_start_idx = 0
        for idx, line in enumerate(lines):
            if 'Fecha' in line and 'Descripción' in line:
                data_start_idx = idx + 1
                break

        # Parse transactions
        reader = csv.reader(lines[data_start_idx:])
        for row in reader:
            if len(row) >= 5:
                try:
                    fecha = row[0].strip()
                    descripcion = row[1].strip()
                    debito = row[2].strip()
                    credito = row[3].strip()
                    balance = row[4].strip()

                    if fecha and descripcion:
                        # Parse date
                        txn_date = datetime.strptime(fecha, '%d/%m/%Y').date()

                        # Determine type and amount
                        if credito and credito not in ('', '0', '0.00'):
                            tx_type = "CREDIT"
                            amount = Decimal(credito.replace(',', ''))
                        else:
                            tx_type = "DEBIT"
                            amount = Decimal(debito.replace(',', '')) if debito and debito not in (
                                '', '0') else Decimal('0')

                        balance_decimal = Decimal(balance.replace(
                            ',', '')) if balance else Decimal('0')

                        transaction = Transaction(
                            txn_date=txn_date,
                            description=descripcion,
                            amount=amount,
                            transaction_type=tx_type,
                            balance=balance_decimal,
                            category="OTHER"
                        )
                        transactions.append(transaction)
                except (ValueError, IndexError):
                    continue

    if not transactions:
        raise ValueError("No transactions found in CSV file")

    period_start = min(t.txn_date for t in transactions)
    period_end = max(t.txn_date for t in transactions)
    summary = _calculate_summary_from_transactions(transactions)

    return BankStatementData(
        account_number=account_number,
        period_start=period_start,
        period_end=period_end,
        transactions=transactions,
        summary=summary,
        confidence=1.0  # CSV parsing is 100% accurate
    )


def parse_banreservas_csv(csv_path: str) -> BankStatementData:
    """
    Parse Banreservas statement from CSV format.

    CSV Format (UTF-16 encoded):
    - Header information with account details
    - Transaction data with Fecha, Descripción, Débito, Crédito, Balance

    Args:
        csv_path: Path to Banreservas CSV file

    Returns:
        Structured bank statement data
    """
    transactions = []
    account_number = "****CSV"

    # Try UTF-16 encoding first (common for Banreservas)
    encodings = ['utf-16', 'utf-16-le', 'utf-8-sig', 'latin-1']
    content = None

    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
                if content and len(content) > 100:
                    break
        except:
            continue

    if not content:
        raise ValueError("Could not read CSV file with any supported encoding")

    lines = content.split('\n')

    # Extract account number
    for line in lines[:10]:
        if 'mero de cuenta' in line or 'cuenta' in line.lower():
            parts = line.split(',')
            if len(parts) >= 2:
                account_full = parts[1].strip()
                if account_full and account_full.isdigit():
                    account_number = f"****{account_full[-4:]}" if len(
                        account_full) >= 4 else account_full
                break

    # Find transaction data start
    data_start_idx = 0
    for idx, line in enumerate(lines):
        if 'Fecha' in line and ('Descripci' in line or 'bito' in line):
            data_start_idx = idx + 1
            break

    # Parse transactions
    for line in lines[data_start_idx:]:
        if not line.strip():
            continue

        # Split by comma, handling quoted values
        try:
            reader = csv.reader([line])
            row = next(reader)

            if len(row) >= 5:
                fecha = row[0].strip()
                descripcion = row[1].strip()
                debito = row[2].strip()
                credito = row[3].strip()
                balance = row[4].strip()

                if fecha and descripcion:
                    # Parse date (DD/MM/YYYY format)
                    try:
                        txn_date = datetime.strptime(fecha, '%d/%m/%Y').date()
                    except ValueError:
                        continue

                    # Clean and parse amounts
                    debito = debito.replace('"', '').replace(',', '').strip()
                    credito = credito.replace('"', '').replace(',', '').strip()
                    balance = balance.replace('"', '').replace(',', '').strip()

                    # Determine type and amount
                    if credito and credito not in ('', '0', '0.00', '-'):
                        tx_type = "CREDIT"
                        amount = Decimal(credito)
                    elif debito and debito.startswith('-'):
                        tx_type = "DEBIT"
                        amount = abs(Decimal(debito))
                    else:
                        tx_type = "DEBIT"
                        amount = Decimal(debito) if debito and debito not in (
                            '', '0') else Decimal('0')

                    balance_decimal = Decimal(balance) if balance and balance not in (
                        '', '0') else Decimal('0')

                    transaction = Transaction(
                        txn_date=txn_date,
                        description=descripcion,
                        amount=amount,
                        transaction_type=tx_type,
                        balance=balance_decimal,
                        category="OTHER"
                    )
                    transactions.append(transaction)
        except (ValueError, IndexError, StopIteration):
            continue

    if not transactions:
        raise ValueError("No transactions found in CSV file")

    period_start = min(t.txn_date for t in transactions)
    period_end = max(t.txn_date for t in transactions)
    summary = _calculate_summary_from_transactions(transactions)

    return BankStatementData(
        account_number=account_number,
        period_start=period_start,
        period_end=period_end,
        transactions=transactions,
        summary=summary,
        confidence=1.0  # CSV parsing is 100% accurate
    )


def _calculate_summary_from_transactions(transactions: list[Transaction]) -> TransactionSummary:
    """Calculate summary statistics from transactions."""
    from app.agents.financial.parsers.bhd import _calculate_summary
    return _calculate_summary(transactions)
