"""Application-level exception hierarchy."""


class MedicalResearchError(Exception):
    """Base exception for all application errors."""


class DocumentNotFoundError(MedicalResearchError):
    """Raised when a requested document does not exist."""


class InvalidFileTypeError(MedicalResearchError):
    """Raised when an uploaded file is not a PDF."""


class ProcessingError(MedicalResearchError):
    """Raised when document processing (conversion, extraction, embedding) fails."""


class LLMError(MedicalResearchError):
    """Raised on LLM API failures."""


class EmbeddingError(MedicalResearchError):
    """Raised on embedding API failures."""


class VectorSearchError(MedicalResearchError):
    """Raised on vector similarity search failures."""
