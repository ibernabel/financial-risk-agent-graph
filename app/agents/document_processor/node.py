"""
Document Processor Agent Node - OCR and document classification.

Stub implementation for Phase 1.
"""

from app.core.state import AgentState


async def document_processor_node(state: AgentState) -> dict:
    """
    Document processor stub - classifies and validates documents.

    Phase 1: Returns mock document processing results.
    Future: Implement OCR, classification, and quality validation.

    Args:
        state: Current agent state

    Returns:
        State update with documents_processed
    """
    # Stub implementation - mock document processing
    documents_processed = [
        {
            "type": doc.get("type", "unknown"),
            "url": doc.get("url", ""),
            "status": "processed",
            "quality_score": 0.95,
            "classification_confidence": 0.98,
        }
        for doc in state.documents
    ]

    return {
        "documents_processed": documents_processed,
        "current_step": "documents_processed",
        "agents_executed": state.agents_executed + ["document_processor"],
    }
