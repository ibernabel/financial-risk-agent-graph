"""
LangGraph orchestration for CreditFlow AI agent workflow.

Defines the graph structure, routing logic, and checkpointing.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.core.state import AgentState
from app.core.config import settings
from app.agents.triage.node import triage_node
from app.agents.document_processor.node import document_processor_node
from app.agents.financial.node import financial_analyst_node
from app.agents.osint.node import osint_researcher_node
from app.agents.irs_engine.node import irs_engine_node
from app.agents.underwriter.node import underwriter_node


def should_continue_after_triage(state: AgentState) -> Literal["document_processor", "END"]:
    """
    Conditional routing after triage.

    If triage rejects the applicant, go directly to END.
    Otherwise, continue to document processing.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.triage_result and state.triage_result.status == "REJECTED":
        return "END"
    return "document_processor"


def create_graph() -> StateGraph:
    """
    Create the LangGraph workflow.

    Graph structure:
        START -> triage -> [REJECTED -> END | PASSED -> document_processor]
        document_processor -> [financial_analyst, osint_researcher] (parallel)
        [financial_analyst, osint_researcher] -> irs_engine
        irs_engine -> underwriter -> END

    Returns:
        Compiled StateGraph
    """
    # Initialize graph with AgentState
    graph = StateGraph(AgentState)

    # Add all agent nodes
    graph.add_node("triage", triage_node)
    graph.add_node("document_processor", document_processor_node)
    graph.add_node("financial_analyst", financial_analyst_node)
    graph.add_node("osint_researcher", osint_researcher_node)
    graph.add_node("irs_engine", irs_engine_node)
    graph.add_node("underwriter", underwriter_node)

    # Define edges
    graph.add_edge(START, "triage")

    # Conditional edge after triage (reject early if ineligible)
    graph.add_conditional_edges(
        "triage",
        should_continue_after_triage,
        {
            "document_processor": "document_processor",
            "END": END,
        },
    )

    # After document processing, run financial and OSINT in parallel
    graph.add_edge("document_processor", "financial_analyst")
    graph.add_edge("document_processor", "osint_researcher")

    # Both parallel agents feed into IRS engine
    graph.add_edge("financial_analyst", "irs_engine")
    graph.add_edge("osint_researcher", "irs_engine")

    # IRS engine feeds into underwriter
    graph.add_edge("irs_engine", "underwriter")

    # Underwriter is the final node
    graph.add_edge("underwriter", END)

    return graph


async def get_compiled_graph():
    """
    Get compiled graph with PostgreSQL checkpointing.

    Uses langgraph-checkpoint-postgres for persistent state management.
    Benefits:
    - Resume workflows after crashes/restarts
    - Time-travel debugging (view state at any point)
    - Complete audit trail of all state changes
    - Thread-safe concurrent execution

    Returns:
        Compiled graph with PostgreSQL checkpointer
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    graph = create_graph()

    # Get PostgreSQL connection string from settings
    db_url = settings.database.url

    # Create checkpointer and setup tables
    checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    await checkpointer.setup()

    # Compile graph with persistent checkpointing
    return graph.compile(checkpointer=checkpointer)


# For synchronous access (if needed)
def get_graph_structure() -> StateGraph:
    """
    Get the graph structure without compilation.

    Useful for visualization and testing.

    Returns:
        StateGraph instance
    """
    return create_graph()
