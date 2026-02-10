#!/usr/bin/env python3
"""
Detailed transaction-by-transaction comparison between PDF OCR and CSV parsers.
Uses cached OCR results to avoid expensive API calls.
"""

import asyncio
import json
from pathlib import Path
from datetime import date
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.agents.financial.parsers.popular import parse_popular_statement
from app.agents.financial.parsers.csv_parser import parse_popular_csv
from app.agents.financial.parsers.bhd import BankStatementData

console = Console()


def serialize_result(result: BankStatementData) -> dict:
    """Serialize BankStatementData to JSON-compatible dict."""
    return {
        "bank_name": result.bank_name,
        "account_number": result.account_number,
        "period_start": result.period_start.isoformat(),
        "period_end": result.period_end.isoformat(),
        "confidence": result.confidence,
        "transactions": [
            {
                "txn_date": tx.txn_date.isoformat(),
                "description": tx.description,
                "amount": str(tx.amount),
                "transaction_type": tx.transaction_type,
                "balance": str(tx.balance),
                "category": tx.category,
            }
            for tx in result.transactions
        ],
        "summary": {
            "total_credits": str(result.summary.total_credits),
            "total_debits": str(result.summary.total_debits),
            "average_balance": str(result.summary.average_balance),
            "salary_deposits": [str(s) for s in result.summary.salary_deposits],
            "payroll_day": result.summary.payroll_day,
        }
    }


def save_cache(cache_file: Path, result: BankStatementData):
    """Save OCR result to cache file."""
    cache_data = serialize_result(result)
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    console.print(f"[dim]💾 Saved to cache: {cache_file.name}[/dim]")


def load_cache(cache_file: Path) -> BankStatementData | None:
    """Load OCR result from cache file."""
    if not cache_file.exists():
        return None

    with open(cache_file, 'r') as f:
        data = json.load(f)

    # Reconstruct BankStatementData
    from app.agents.financial.parsers.bhd import Transaction, TransactionSummary

    transactions = [
        Transaction(
            txn_date=date.fromisoformat(tx["txn_date"]),
            description=tx["description"],
            amount=Decimal(tx["amount"]),
            transaction_type=tx["transaction_type"],
            balance=Decimal(tx["balance"]),
            category=tx["category"],
        )
        for tx in data["transactions"]
    ]

    summary = TransactionSummary(
        total_credits=Decimal(data["summary"]["total_credits"]),
        total_debits=Decimal(data["summary"]["total_debits"]),
        average_balance=Decimal(data["summary"]["average_balance"]),
        salary_deposits=[Decimal(s)
                         for s in data["summary"]["salary_deposits"]],
        payroll_day=data["summary"]["payroll_day"],
    )

    result = BankStatementData(
        bank_name=data["bank_name"],
        account_number=data["account_number"],
        period_start=date.fromisoformat(data["period_start"]),
        period_end=date.fromisoformat(data["period_end"]),
        transactions=transactions,
        summary=summary,
        confidence=data["confidence"],
    )

    console.print(f"[dim]📂 Loaded from cache: {cache_file.name}[/dim]")
    return result


async def detailed_comparison():
    """Compare CSV and PDF OCR parsers transaction by transaction."""
    base_path = Path(
        "creditflow_context/personal_loan_application_data/bank_statements/popular_bank")
    pdf_path = base_path / "popular_bank_statement.pdf"
    csv_path = base_path / "popular_bank_statement.csv"
    cache_file = base_path / ".popular_ocr_cache.json"

    # Try to load from cache first
    console.print(
        "\n[bold yellow]Checking for cached OCR results...[/bold yellow]")
    pdf_result = load_cache(cache_file)

    if pdf_result is None:
        # No cache, need to run OCR (costs money!)
        console.print(
            "[bold red]⚠️  No cache found. Running OCR (this will cost API credits)...[/bold red]")

        # Temporarily rename CSV to force PDF OCR
        csv_backup = csv_path.with_suffix('.csv.backup')
        if csv_path.exists():
            csv_path.rename(csv_backup)

        try:
            pdf_result = await parse_popular_statement(str(pdf_path))
            csv_backup.rename(csv_path)
        except Exception as e:
            if csv_backup.exists():
                csv_backup.rename(csv_path)
            raise e

        # Save to cache
        save_cache(cache_file, pdf_result)

    # Parse CSV (fast and free!)
    console.print("[bold yellow]Parsing CSV...[/bold yellow]\n")
    csv_result = parse_popular_csv(str(csv_path))

    # Summary comparison
    summary_table = Table(title="📊 Summary Comparison", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("CSV", style="green", justify="right")
    summary_table.add_column("PDF OCR", style="yellow", justify="right")
    summary_table.add_column("Difference", style="red", justify="right")

    csv_count = len(csv_result.transactions)
    pdf_count = len(pdf_result.transactions)
    summary_table.add_row("Transactions", str(csv_count), str(
        pdf_count), f"{pdf_count - csv_count:+d}")

    csv_credits = float(csv_result.summary.total_credits)
    pdf_credits = float(pdf_result.summary.total_credits)
    summary_table.add_row(
        "Total Credits",
        f"${csv_credits:,.2f}",
        f"${pdf_credits:,.2f}",
        f"${pdf_credits - csv_credits:+,.2f}"
    )

    csv_debits = float(csv_result.summary.total_debits)
    pdf_debits = float(pdf_result.summary.total_debits)
    summary_table.add_row(
        "Total Debits",
        f"${csv_debits:,.2f}",
        f"${pdf_debits:,.2f}",
        f"${pdf_debits - csv_debits:+,.2f}"
    )

    console.print(summary_table)

    # Find mismatched transactions
    console.print(
        "\n[bold cyan]Looking for mismatched transactions...[/bold cyan]\n")

    # Group by date for comparison
    csv_by_date = {}
    for tx in csv_result.transactions:
        date_key = tx.txn_date.strftime("%Y-%m-%d")
        if date_key not in csv_by_date:
            csv_by_date[date_key] = []
        csv_by_date[date_key].append(tx)

    pdf_by_date = {}
    for tx in pdf_result.transactions:
        date_key = tx.txn_date.strftime("%Y-%m-%d")
        if date_key not in pdf_by_date:
            pdf_by_date[date_key] = []
        pdf_by_date[date_key].append(tx)

    # Find dates with different transaction counts or types
    all_dates = set(csv_by_date.keys()) | set(pdf_by_date.keys())

    differences = []
    for date_str in sorted(all_dates):
        csv_txns = csv_by_date.get(date_str, [])
        pdf_txns = pdf_by_date.get(date_str, [])

        if len(csv_txns) != len(pdf_txns):
            differences.append((date_str, csv_txns, pdf_txns))
            continue

        # Compare transaction types and amounts
        for csv_tx, pdf_tx in zip(csv_txns, pdf_txns):
            if csv_tx.transaction_type != pdf_tx.transaction_type:
                differences.append((date_str, [csv_tx], [pdf_tx]))
            elif abs(float(csv_tx.amount) - float(pdf_tx.amount)) > 0.01:
                differences.append((date_str, [csv_tx], [pdf_tx]))

    if differences:
        console.print(
            f"[bold red]Found {len(differences)} date(s) with differences:[/bold red]\n")

        for date_str, csv_txns, pdf_txns in differences:
            console.print(f"[bold yellow]Date: {date_str}[/bold yellow]")

            # CSV transactions
            if csv_txns:
                console.print("  [green]CSV:[/green]")
                for tx in csv_txns:
                    console.print(
                        f"    {tx.transaction_type}: ${float(tx.amount):,.2f} - {tx.description[:50]}")
            else:
                console.print("  [green]CSV:[/green] (no transactions)")

            # PDF transactions
            if pdf_txns:
                console.print("  [yellow]PDF OCR:[/yellow]")
                for tx in pdf_txns:
                    console.print(
                        f"    {tx.transaction_type}: ${float(tx.amount):,.2f} - {tx.description[:50]}")
            else:
                console.print("  [yellow]PDF OCR:[/yellow] (no transactions)")

            console.print()
    else:
        console.print("[bold green]✅ All transactions match![/bold green]")

    console.print(
        f"\n[dim]💡 Tip: Delete {cache_file.name} to re-run OCR with fresh API call[/dim]")


if __name__ == "__main__":
    asyncio.run(detailed_comparison())
