"""
Financial risk pattern detection.

Detects suspicious patterns in bank transaction history:
- FIN-01: Fast Withdrawal (>90% withdrawal within 24h of salary deposit)
- FIN-02: Informal Lender (recurring round transfers)
- FIN-03: NSF/Overdraft flags
- FIN-04: Salary Inconsistency (declared vs actual >20% variance)
- FIN-05: Multiple Hidden Accounts
"""

from datetime import timedelta
from decimal import Decimal
from collections import defaultdict

from app.agents.financial.parsers.bhd import Transaction


class PatternDetector:
    """Detects financial risk patterns in transaction history."""

    @staticmethod
    def detect_fast_withdrawal(transactions: list[Transaction]) -> list[str]:
        """
        Detect Fast Withdrawal pattern (FIN-01).

        Pattern: >90% of salary withdrawn within 24h of deposit.

        Args:
            transactions: List of transactions sorted by date

        Returns:
            List of dates (ISO format) where pattern was detected

        Risk Level: HIGH
        """
        detected_dates = []

        # Group transactions by date
        txns_by_date: dict[str, list[Transaction]] = defaultdict(list)
        for txn in transactions:
            txns_by_date[txn.date.isoformat()].append(txn)

        # Check each day for large credits followed by large debits
        for date_str, day_txns in txns_by_date.items():
            credits = [t for t in day_txns if t.type == "CREDIT"]
            debits = [t for t in day_txns if t.type == "DEBIT"]

            for credit in credits:
                # Check if this looks like a salary (>= 10,000 DOP)
                if credit.amount < Decimal("10000"):
                    continue

                # Sum debits within 24h
                withdrawal_total = Decimal("0")
                credit_date = credit.date

                for debit in debits:
                    if abs((debit.date - credit_date).days) <= 1:
                        withdrawal_total += abs(debit.amount)

                # Check if >90% withdrawn
                withdrawal_ratio = withdrawal_total / credit.amount
                if withdrawal_ratio > Decimal("0.90"):
                    detected_dates.append(date_str)
                    break  # One detection per day

        return detected_dates

    @staticmethod
    def detect_informal_lender(transactions: list[Transaction]) -> bool:
        """
        Detect Informal Lender pattern (FIN-02).

        Pattern: Recurring transfers to same recipient with round amounts.

        Criteria:
        - Same recipient (fuzzy match on description)
        - Round amounts (e.g., 5000, 10000, 15000)
        - Frequency: Weekly or biweekly (at least 3 occurrences)

        Args:
            transactions: List of transactions

        Returns:
            True if pattern detected, False otherwise

        Risk Level: CRITICAL
        """
        # Filter debits (transfers out)
        debits = [t for t in transactions if t.type == "DEBIT"]

        # Group by similar descriptions and round amounts
        transfer_groups: dict[tuple[str, Decimal],
                              list[Transaction]] = defaultdict(list)

        for debit in debits:
            # Check if amount is round (divisible by 1000)
            if debit.amount % Decimal("1000") != 0:
                continue

            # Normalize description (lowercase, remove extra spaces)
            desc_normalized = " ".join(debit.description.lower().split())

            # Group by description prefix (first 20 chars) and amount
            key = (desc_normalized[:20], abs(debit.amount))
            transfer_groups[key].append(debit)

        # Check for recurring patterns (at least 3 occurrences)
        for group_txns in transfer_groups.values():
            if len(group_txns) >= 3:
                return True

        return False

    @staticmethod
    def detect_nsf_flags(transactions: list[Transaction]) -> int:
        """
        Detect NSF/Overdraft flags (FIN-03).

        Counts transactions with insufficient fund indicators.

        Args:
            transactions: List of transactions

        Returns:
            Count of NSF/overdraft occurrences

        Risk Level: MEDIUM
        """
        nsf_keywords = [
            "nsf",
            "insufficient",
            "overdraft",
            "sobregiro",
            "fondos insuficientes",
            "rechazado",
            "devuelto",
        ]

        nsf_count = 0
        for txn in transactions:
            desc_lower = txn.description.lower()
            if any(keyword in desc_lower for keyword in nsf_keywords):
                nsf_count += 1

        return nsf_count

    @staticmethod
    def detect_salary_inconsistency(
        declared_salary: Decimal,
        detected_salary_deposits: list[Decimal],
    ) -> tuple[bool, Decimal]:
        """
        Detect Salary Inconsistency (FIN-04).

        Check if declared salary differs >20% from actual deposits.

        Args:
            declared_salary: Applicant's declared monthly salary
            detected_salary_deposits: List of detected salary amounts

        Returns:
            Tuple of (is_inconsistent, variance_percentage)

        Risk Level: HIGH
        """
        if not detected_salary_deposits:
            # No salary detected - flag as inconsistent
            return (True, Decimal("100.0"))

        # Use average of detected salaries
        avg_detected = sum(detected_salary_deposits) / \
            len(detected_salary_deposits)

        # Calculate variance percentage
        variance = abs(declared_salary - avg_detected) / declared_salary * 100

        is_inconsistent = variance > Decimal("20.0")

        return (is_inconsistent, variance)

    @staticmethod
    def detect_hidden_accounts(transactions: list[Transaction]) -> bool:
        """
        Detect Multiple Hidden Accounts (FIN-05).

        Pattern: Frequent self-transfers to similar account numbers.

        Criteria:
        - Transfers with descriptions containing account numbers
        - Same recipient account appears multiple times
        - Suggests income splitting across accounts

        Args:
            transactions: List of transactions

        Returns:
            True if pattern detected, False otherwise

        Risk Level: MEDIUM
        """
        # Look for transfer keywords
        transfer_keywords = ["transferencia", "transfer", "traspaso"]

        # Count transfers to same accounts
        account_transfers: dict[str, int] = defaultdict(int)

        for txn in transactions:
            desc_lower = txn.description.lower()

            # Check if it's a transfer
            if not any(keyword in desc_lower for keyword in transfer_keywords):
                continue

            # Extract potential account numbers (4+ digits)
            import re
            account_numbers = re.findall(r"\d{4,}", txn.description)

            for account in account_numbers:
                account_transfers[account] += 1

        # Check for recurring transfers (>= 3 times to same account)
        for count in account_transfers.values():
            if count >= 3:
                return True

        return False

    @staticmethod
    def detect_all_patterns(
        transactions: list[Transaction],
        declared_salary: Decimal,
        detected_salary_deposits: list[Decimal],
    ) -> dict[str, any]:
        """
        Run all pattern detection algorithms.

        Args:
            transactions: List of transactions
            declared_salary: Declared monthly salary
            detected_salary_deposits: Detected salary amounts

        Returns:
            Dictionary with all detected patterns and flags
        """
        fast_withdrawal_dates = PatternDetector.detect_fast_withdrawal(
            transactions)
        informal_lender = PatternDetector.detect_informal_lender(transactions)
        nsf_count = PatternDetector.detect_nsf_flags(transactions)
        salary_inconsistent, salary_variance = PatternDetector.detect_salary_inconsistency(
            declared_salary, detected_salary_deposits
        )
        hidden_accounts = PatternDetector.detect_hidden_accounts(transactions)

        # Build flags list
        flags = []
        if fast_withdrawal_dates:
            flags.append(
                f"FAST_WITHDRAWAL: Detected on {', '.join(fast_withdrawal_dates)}")
        if informal_lender:
            flags.append("INFORMAL_LENDER_DETECTED")
        if nsf_count > 0:
            flags.append(f"NSF_OVERDRAFT: {nsf_count} occurrences")
        if salary_inconsistent:
            flags.append(
                f"SALARY_INCONSISTENCY: {salary_variance:.1f}% variance")
        if hidden_accounts:
            flags.append("MULTIPLE_HIDDEN_ACCOUNTS")

        return {
            "fast_withdrawal_dates": fast_withdrawal_dates,
            "informal_lender_detected": informal_lender,
            "nsf_count": nsf_count,
            "salary_inconsistent": salary_inconsistent,
            "salary_variance_pct": float(salary_variance),
            "hidden_accounts_detected": hidden_accounts,
            "flags": flags,
        }
