"""
OCR tool using GPT-4o-mini for document text extraction.

Provides structured data extraction from PDF documents using OpenAI's vision model.
"""

import base64
from typing import Type, TypeVar
from pathlib import Path

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


async def extract_document_data(
    pdf_path: str,
    extraction_prompt: str,
    response_schema: Type[T],
) -> T:
    """
    Extract structured data from document using GPT-4o-mini vision.

    Args:
        pdf_path: Path to PDF file (local or URL)
        extraction_prompt: System prompt describing what to extract
        response_schema: Pydantic model class for structured output

    Returns:
        Instance of response_schema with extracted data

    Raises:
        ValueError: If extraction fails or response doesn't match schema

    Examples:
        >>> class BankData(BaseModel):
        ...     account_number: str
        ...     balance: float
        >>> 
        >>> data = await extract_document_data(
        ...     pdf_path="/path/to/statement.pdf",
        ...     extraction_prompt="Extract account number and balance",
        ...     response_schema=BankData
        ... )
        >>> print(data.account_number)
    """
    # Initialize LLM with structured output
    llm = ChatOpenAI(
        model=settings.ocr_llm_model,
        temperature=settings.ocr_temperature,
        max_tokens=settings.ocr_max_tokens,
    )
    llm_with_structure = llm.with_structured_output(response_schema)

    # Prepare image content
    if pdf_path.startswith("http"):
        # URL-based image
        image_content = {"type": "image_url", "image_url": {"url": pdf_path}}
    else:
        # Local file - encode as base64
        with open(pdf_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Detect file type
        suffix = Path(pdf_path).suffix.lower()
        mime_type = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(suffix, "application/pdf")

        image_content = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
        }

    # Create message with prompt and image
    message = HumanMessage(
        content=[
            {"type": "text", "text": extraction_prompt},
            image_content,
        ]
    )

    # Invoke LLM and return structured result
    result = await llm_with_structure.ainvoke([message])
    return result


async def extract_with_confidence(
    pdf_path: str,
    extraction_prompt: str,
    response_schema: Type[T],
) -> tuple[T, float]:
    """
    Extract structured data with confidence score.

    Args:
        pdf_path: Path to PDF file
        extraction_prompt: Extraction instructions
        response_schema: Pydantic model for output

    Returns:
        Tuple of (extracted_data, confidence_score)
        Confidence is estimated from LLM response metadata

    Note:
        Confidence scoring is a simplified heuristic for Phase 2.
        TODO: Implement proper confidence calibration in production.
    """
    # For Phase 2, we'll extract data and return fixed confidence
    # In production, analyze LLM logprobs or use multiple passes
    data = await extract_document_data(pdf_path, extraction_prompt, response_schema)

    # Simplified confidence: 0.95 if all required fields populated
    confidence = 0.95 if _all_fields_populated(data) else 0.70

    return (data, confidence)


def _all_fields_populated(model: BaseModel) -> bool:
    """Check if all required fields in Pydantic model are populated."""
    for field_name, field_info in model.model_fields.items():
        value = getattr(model, field_name)

        # Check if required field is None or empty
        if field_info.is_required():
            if value is None:
                return False
            if isinstance(value, (str, list, dict)) and not value:
                return False

    return True
