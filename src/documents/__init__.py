"""Safe document normalization for recruitment inputs."""

from .extract_text import ExtractedDocument, UnsupportedDocument, extract_document

__all__ = ["ExtractedDocument", "UnsupportedDocument", "extract_document"]
