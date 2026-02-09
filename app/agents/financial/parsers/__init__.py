"""Parser package initialization."""

from app.agents.financial.parsers.bhd import parse_bhd_statement, BankStatementData
from app.agents.financial.parsers.popular import parse_popular_statement
from app.agents.financial.parsers.banreservas import parse_banreservas_statement

__all__ = [
    "parse_bhd_statement",
    "parse_popular_statement",
    "parse_banreservas_statement",
    "BankStatementData",
]
