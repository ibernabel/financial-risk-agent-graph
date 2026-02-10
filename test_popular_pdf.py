#!/usr/bin/env python3
"""
Test script for Popular Bank PDF parser using OCR.

This script tests the PDF parser directly without CSV fallback.
"""

from app.agents.financial.parsers.popular import parse_popular_statement
from app.core.config import settings
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


console = Console()


async def test_openai_api_key():
    """Verify OpenAI API key is configured."""
    console.print("\n[bold cyan]Step 1: Verifying OpenAI API Key[/bold cyan]")

    api_key = settings.llm.openai_api_key

    if not api_key:
        console.print(Panel(
            "[bold red]❌ ERROR:[/bold red] OPENAI_API_KEY is not set in .env file",
            title="[bold red]Configuration Error[/bold red]",
            border_style="red"
        ))
        return False

    # Mask the API key for display
    masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(
        api_key) > 14 else "***"

    console.print(Panel(
        f"[bold green]✅ API Key Found:[/bold green] {masked_key}\n"
        f"[bold]Model:[/bold] {settings.llm.ocr_llm_model}\n"
        f"[bold]Temperature:[/bold] {settings.llm.ocr_temperature}\n"
        f"[bold]Max Tokens:[/bold] {settings.llm.ocr_max_tokens}",
        title="[bold green]OpenAI Configuration[/bold green]",
        border_style="green"
    ))

    return True


async def test_popular_pdf_parser():
    """Test Popular Bank PDF parser with OCR."""
    console.print(
        "\n[bold cyan]Step 2: Testing Popular Bank PDF Parser (OCR)[/bold cyan]")

    # Path to Popular Bank PDF
    pdf_path = Path(
        "creditflow_context/personal_loan_application_data/bank_statements/popular_bank/popular_bank_statement.pdf")

    if not pdf_path.exists():
        console.print(Panel(
            f"[bold red]❌ ERROR:[/bold red] PDF file not found at {pdf_path}",
            title="[bold red]File Not Found[/bold red]",
            border_style="red"
        ))
        return False

    console.print(f"[bold]PDF File:[/bold] {pdf_path}")
    console.print(f"[bold]File Size:[/bold] {pdf_path.stat().st_size:,} bytes")

    # Check for CSV file and temporarily rename it to force PDF parsing
    csv_path = pdf_path.with_suffix('.csv')
    csv_backup = None

    if csv_path.exists():
        console.print(
            f"\n[yellow]⚠️  CSV file found. Temporarily renaming to force PDF OCR...[/yellow]")
        csv_backup = csv_path.with_suffix('.csv.backup')
        csv_path.rename(csv_backup)

    try:
        # Parse the statement
        console.print(
            "\n[bold yellow]📄 Starting PDF OCR parsing...[/bold yellow]")
        console.print("[dim]This may take a few moments...[/dim]\n")

        result = await parse_popular_statement(str(pdf_path))

        # Display results
        console.print(Panel(
            f"[bold]Bank:[/bold] {result.bank_name}\n"
            f"[bold]Account:[/bold] {result.account_number}\n"
            f"[bold]Period:[/bold] {result.period_start} to {result.period_end}\n"
            f"[bold]Total Transactions:[/bold] {len(result.transactions)}\n"
            f"[bold]Confidence:[/bold] {result.confidence:.1%}",
            title="[bold green]✅ Parsing Successful[/bold green]",
            border_style="green"
        ))

        # Display summary
        summary_table = Table(title="📊 Financial Summary",
                              show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan", width=25)
        summary_table.add_column("Value", style="green", justify="right")

        summary_table.add_row(
            "Total Credits", f"DOP ${result.summary.total_credits:,.2f}")
        summary_table.add_row(
            "Total Debits", f"DOP ${result.summary.total_debits:,.2f}")
        summary_table.add_row(
            "Average Balance", f"DOP ${result.summary.average_balance:,.2f}")

        if result.summary.salary_deposits:
            summary_table.add_row(
                "Detected Salaries", f"{len(result.summary.salary_deposits)} deposits")
            for i, salary in enumerate(result.summary.salary_deposits, 1):
                summary_table.add_row(f"  Salary {i}", f"DOP ${salary:,.2f}")

        if result.summary.payroll_day:
            summary_table.add_row(
                "Payroll Day", str(result.summary.payroll_day))

        console.print(summary_table)

        # Display sample transactions
        console.print(
            "\n[bold yellow]📝 Sample Transactions (First 5)[/bold yellow]")
        tx_table = Table(show_header=True, header_style="bold blue")
        tx_table.add_column("Date", style="cyan", width=12)
        tx_table.add_column("Type", style="magenta", width=8)
        tx_table.add_column("Amount", style="green", justify="right", width=15)
        tx_table.add_column("Description", style="white", width=40)

        for tx in result.transactions[:5]:
            amount_str = f"DOP ${tx.amount:,.2f}"
            if tx.transaction_type == "DEBIT":
                amount_str = f"[red]-{amount_str}[/red]"
            else:
                amount_str = f"[green]+{amount_str}[/green]"

            tx_table.add_row(
                tx.txn_date.strftime("%Y-%m-%d"),
                tx.transaction_type,
                amount_str,
                tx.description[:40]
            )

        console.print(tx_table)

        return True

    except Exception as e:
        console.print(Panel(
            f"[bold red]Error:[/bold red] {str(e)}\n\n"
            f"[dim]{type(e).__name__}[/dim]",
            title="[bold red]❌ Parsing Failed[/bold red]",
            border_style="red"
        ))
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        return False

    finally:
        # Restore CSV file if it was renamed
        if csv_backup and csv_backup.exists():
            console.print(f"\n[yellow]Restoring CSV file...[/yellow]")
            csv_backup.rename(csv_path)


async def main():
    """Main test function."""
    console.print(Panel(
        "[bold cyan]Popular Bank PDF Parser Test[/bold cyan]\n\n"
        "This test will:\n"
        "1. Verify OpenAI API key configuration\n"
        "2. Parse Popular Bank PDF using OCR (skip CSV)\n"
        "3. Display parsed transaction data",
        title="[bold green]🧪 Test Suite[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # Test 1: Verify API key
    api_ok = await test_openai_api_key()
    if not api_ok:
        console.print(
            "\n[bold red]❌ Test aborted due to configuration error[/bold red]")
        return

    # Test 2: Parse PDF
    parse_ok = await test_popular_pdf_parser()

    # Final summary
    console.print("\n" + "="*80)
    if parse_ok:
        console.print(Panel(
            "[bold green]✅ All tests passed![/bold green]\n\n"
            "The Popular Bank PDF parser is working correctly with OCR.",
            title="[bold green]Test Results[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold red]❌ Tests failed[/bold red]\n\n"
            "Please review the errors above.",
            title="[bold red]Test Results[/bold red]",
            border_style="red"
        ))


if __name__ == "__main__":
    asyncio.run(main())
