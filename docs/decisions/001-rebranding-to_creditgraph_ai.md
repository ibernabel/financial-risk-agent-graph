# ADR 001: Rebranding to CreditGraph AI

## Status

Accepted

## Context

The project was originally named **CreditFlow AI**. While it captured the essence of the credit evaluation workflow, the name felt generic and aligned with simple linear automation tools.

As the project evolved to use **LangGraph** for multi-agent orchestration, the internal logic became more like a network or a graph of interconnected decisions rather than a simple flow. The system's strength lies in its ability to "connect the dots" between isolated data sources (bank statements, OSINT, credit reports).

## Decision

Rename the project to **CreditGraph AI**.

This change reflects:

1.  **Technical Architecture**: Direct reference to the use of LangGraph.
2.  **Conceptual Methodology**: Symbolizes the system's ability to analyze complex data networks to detect hidden risk patterns.
3.  **Competitive Differentiation**: Distinguishes the product from collection management or simple workflow solutions.

## Implementation Detail

The following changes were applied:

- **Global String Replacement**: Updated all occurrences of "CreditFlow AI" and "CreditFlow" to "CreditGraph AI" or "CreditGraph".
- **Agent Narratives**: Updated LLM persona references in the Underwriter and IRS Engine.
- **Metadata**: Updated `pyproject.toml`, API titles, and documentation index.
- **Orchestration**: Updated the LangGraph checkpoint namespace from `creditflow` to `creditgraph`.

## Consequences

- All documentation and code strings now consistently use the new branding.
- PostgreSQL checkpoints for existing threads may be invalidated if they were tied to the `creditflow` namespace (acceptable for this phase of development).
- The product is now positioned as a deeper intelligence tool rather than just a workflow automation.
