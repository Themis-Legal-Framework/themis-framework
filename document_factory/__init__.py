"""Document Factory - Clean, efficient legal document generation.

This module provides a streamlined approach to generating legal documents:
- Single LLM call per document (fast and cost-effective)
- Explicit document type specification (no guessing)
- Comprehensive template library (20+ document types)
- Professional quality output

Usage:
    from document_factory import DocumentFactory, DocumentRequest

    factory = DocumentFactory()
    doc = await factory.generate(
        matter=case_data,
        request=DocumentRequest(
            type="client_letter",
            addressee="Mrs. Smith"
        )
    )
    print(doc.content)

Or for simple usage:
    from document_factory import generate_document

    doc = await generate_document(
        matter=case_data,
        document_type="motion_sanctions"
    )
"""

from document_factory.factory import (
    DocumentFactory,
    DocumentRequest,
    GeneratedDocument,
    generate_document,
)
from document_factory.registry import (
    DocumentCategory,
    DocumentTemplate,
    get_document_template,
    list_document_types,
    DOCUMENT_TYPES,
)

__all__ = [
    # Main classes
    "DocumentFactory",
    "DocumentRequest",
    "GeneratedDocument",
    # Convenience function
    "generate_document",
    # Registry
    "DocumentCategory",
    "DocumentTemplate",
    "DOCUMENT_TYPES",
    "get_document_template",
    "list_document_types",
]
