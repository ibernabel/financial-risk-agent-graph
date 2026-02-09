#!/usr/bin/env python3
"""
Bank Statement Analysis Demo

This script demonstrates the bank statement parsing and analysis capabilities
of CreditFlow AI by processing real bank statements from the test data.
"""

import asyncio
import json
from pathlib import Path
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from app.agents.financial.parsers.bhd import parse_bhd_statement, BankStatementData
from app.agents.financial.parsers.popular import parse_popular_statement
from app.agents.financial.parsers.banreservas import parse_banreservas_statement
from app.agents.financial.pattern_detector import PatternDetector


# Initialize Rich console for beautiful output
console = Console()


async def analyze_bank_statement(bank_name: str, file_path: Path, declared_salary: Decimal):
    """
    Analyze a bank statement and display results.

    Args:
        bank_name: Name of the bank (bhd, popular, banreservas)
        file_path: Path to the bank statement PDF
        declared_salary: Declared monthly salary for comparison
    """
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(
        f"[bold yellow]Analyzing {bank_name.upper()} Bank Statement[/bold yellow]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")

    # Select appropriate parser function
    parser_map = {
        "bhd": parse_bhd_statement,
        "popular": parse_popular_statement,
        "banreservas": parse_banreservas_statement,
    }

    parser_func = parser_map.get(bank_name.lower())
    if not parser_func:
        console.print(f"[bold red]❌ Unknown bank: {bank_name}[/bold red]")
        return

    # Parse the bank statement
    console.print("[bold blue]📄 Parsing bank statement...[/bold blue]")

    try:
        result = await parser_func(str(file_path))

        # Display basic information
        console.print(Panel(
            f"[bold]Account:[/bold] {result.account_number}\n"
            f"[bold]Period:[/bold] {result.period_start} to {result.period_end}\n"
            f"[bold]Total Transactions:[/bold] {len(result.transactions)}\n"
            f"[bold]Confidence:[/bold] {result.confidence:.1%}",
            title="[bold green]✅ Statement Parsed Successfully[/bold green]",
            border_style="green"
        ))

        # Display summary statistics
        summary_table = Table(title="📊 Financial Summary",
                              show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan", width=30)
        summary_table.add_column("Value", style="green", justify="right")

        summary_table.add_row(
            "Total Credits", f"DOP ${result.summary.total_credits:,.2f}")
        summary_table.add_row(
            "Total Debits", f"DOP ${result.summary.total_debits:,.2f}")
        summary_table.add_row(
            "Average Balance", f"DOP ${result.summary.average_balance:,.2f}")

        # Show detected salary (first one if multiple)
        if result.summary.salary_deposits:
            detected_salary = result.summary.salary_deposits[0]
            summary_table.add_row(
                "Detected Salary", f"DOP ${detected_salary:,.2f}")
        else:
            summary_table.add_row("Detected Salary", "N/A")

        summary_table.add_row("Payroll Day", str(
            result.summary.payroll_day) if result.summary.payroll_day else "N/A")

        console.print(summary_table)

        # Display recent transactions (last 10)
        console.print(
            "\n[bold yellow]📝 Recent Transactions (Last 10)[/bold yellow]")
        tx_table = Table(show_header=True, header_style="bold blue")
        tx_table.add_column("Date", style="cyan", width=12)
        tx_table.add_column("Description", style="white", width=35)
        tx_table.add_column("Type", style="magenta", width=12)
        tx_table.add_column("Amount", style="green", justify="right", width=15)

        for tx in result.transactions[-10:]:
            amount_str = f"DOP ${tx.amount:,.2f}"
            if tx.transaction_type == "DEBIT":
                amount_str = f"[red]-{amount_str}[/red]"
            else:
                amount_str = f"[green]+{amount_str}[/green]"

            tx_table.add_row(
                tx.txn_date.strftime("%Y-%m-%d"),
                tx.description[:35],
                tx.transaction_type,
                amount_str
            )

        console.print(tx_table)

        # Run pattern detection
        console.print(
            "\n[bold yellow]🔍 Running Pattern Detection...[/bold yellow]")

        # Use salary_deposits list for pattern detection
        detected_salary_deposits = result.summary.salary_deposits

        patterns = PatternDetector.detect_all_patterns(
            transactions=result.transactions,
            declared_salary=declared_salary,
            detected_salary_deposits=detected_salary_deposits
        )

        # Display pattern detection results
        pattern_table = Table(title="🚨 Risk Pattern Detection",
                              show_header=True, header_style="bold red")
        pattern_table.add_column("Pattern", style="yellow", width=30)
        pattern_table.add_column("Status", style="white", width=15)
        pattern_table.add_column("Details", style="cyan", width=30)

        # Fast Withdrawal
        fast_withdrawal_status = "🔴 DETECTED" if patterns["fast_withdrawal_dates"] else "✅ CLEAR"
        fast_withdrawal_details = f"{len(patterns['fast_withdrawal_dates'])} occurrences" if patterns[
            "fast_withdrawal_dates"] else "None"
        pattern_table.add_row("Fast Withdrawal (FIN-01)",
                              fast_withdrawal_status, fast_withdrawal_details)

        # Informal Lender
        informal_lender_status = "🔴 DETECTED" if patterns["informal_lender_detected"] else "✅ CLEAR"
        pattern_table.add_row("Informal Lender (FIN-02)",
                              informal_lender_status, "")

        # NSF/Overdraft
        nsf_status = "🔴 DETECTED" if patterns["nsf_count"] > 0 else "✅ CLEAR"
        nsf_details = f"{patterns['nsf_count']} occurrences" if patterns["nsf_count"] > 0 else "None"
        pattern_table.add_row("NSF/Overdraft (FIN-03)",
                              nsf_status, nsf_details)

        # Salary Inconsistency
        salary_status = "🔴 DETECTED" if patterns["salary_inconsistent"] else "✅ CLEAR"
        salary_details = f"{patterns['salary_variance_pct']:.1f}% variance" if patterns[
            "salary_inconsistent"] else "Within tolerance"
        pattern_table.add_row("Salary Inconsistency (FIN-04)",
                              salary_status, salary_details)

        # Hidden Accounts
        hidden_status = "🔴 DETECTED" if patterns["hidden_accounts_detected"] else "✅ CLEAR"
        pattern_table.add_row("Hidden Accounts (FIN-05)", hidden_status, "")

        console.print(pattern_table)

        # Display flags
        if patterns["flags"]:
            console.print("\n[bold red]⚠️  Risk Flags:[/bold red]")
            for flag in patterns["flags"]:
                console.print(f"  • {flag}")
        else:
            console.print(
                "\n[bold green]✅ No risk flags detected[/bold green]")

        # Display raw pattern data
        console.print("\n[bold cyan]📋 Raw Pattern Detection Data:[/bold cyan]")
        pattern_json = json.dumps(patterns, indent=2, default=str)
        syntax = Syntax(pattern_json, "json",
                        theme="monokai", line_numbers=True)
        console.print(syntax)

    except Exception as e:
        console.print(Panel(
            f"[bold red]Error:[/bold red] {str(e)}",
            title="[bold red]❌ Analysis Failed[/bold red]",
            border_style="red"
        ))
        raise


async def main():
    """Main demo function."""
    console.print(Panel(
        "[bold cyan]CreditFlow AI - Bank Statement Analysis Demo[/bold cyan]\n\n"
        "This demo analyzes bank statements from three Dominican banks:\n"
        "• Banco BHD León\n"
        "• Banco Popular Dominicano\n"
        "• Banco de Reservas (Banreservas)\n\n"
        "The analysis includes:\n"
        "✓ Transaction extraction and categorization\n"
        "✓ Salary detection and payroll day identification\n"
        "✓ Financial pattern detection (FIN-01 to FIN-05)\n"
        "✓ Risk flag generation",
        title="[bold green]🏦 Welcome to CreditFlow AI[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    # Define test data paths
    base_path = Path(
        "creditflow_context/personal_loan_application_data/bank_statements")

    test_cases = [
        {
            "bank": "bhd",
            "file": base_path / "bhd_bank" / "bhd_bank_statement.pdf",
            "declared_salary": Decimal("35000.00")
        },
        {
            "bank": "popular",
            "file": base_path / "popular_bank" / "popular_bank_statement.pdf",
            "declared_salary": Decimal("35000.00")
        },
        {
            "bank": "banreservas",
            "file": base_path / "banreservas_bank" / "banreservas_bank_statement.pdf",
            "declared_salary": Decimal("35000.00")
        },
    ]

    # Note: The system currently uses OCR for PDF files. CSV files are available
    # and would be faster to process, but require a different parser implementation.

    # Let user choose which bank to analyze
    console.print("\n[bold yellow]Select a bank to analyze:[/bold yellow]")
    console.print("1. Banco BHD León")
    console.print("2. Banco Popular Dominicano")
    console.print("3. Banco de Reservas (Banreservas)")
    console.print("4. Analyze all banks")

    choice = console.input(
        "\n[bold cyan]Enter your choice (1-4):[/bold cyan] ")

    try:
        choice_num = int(choice)
        if choice_num == 4:
            # Analyze all banks
            for test_case in test_cases:
                if test_case["file"].exists():
                    await analyze_bank_statement(
                        test_case["bank"],
                        test_case["file"],
                        test_case["declared_salary"]
                    )
                else:
                    console.print(
                        f"\n[bold red]❌ File not found: {test_case['file']}[/bold red]")
        elif 1 <= choice_num <= 3:
            # Analyze selected bank
            test_case = test_cases[choice_num - 1]
            if test_case["file"].exists():
                await analyze_bank_statement(
                    test_case["bank"],
                    test_case["file"],
                    test_case["declared_salary"]
                )
            else:
                console.print(
                    f"\n[bold red]❌ File not found: {test_case['file']}[/bold red]")
        else:
            console.print(
                "[bold red]Invalid choice. Please enter 1-4.[/bold red]")
    except ValueError:
        console.print(
            "[bold red]Invalid input. Please enter a number.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

    console.print("\n[bold green]✅ Demo completed![/bold green]\n")


if __name__ == "__main__":
    asyncio.run(main())
