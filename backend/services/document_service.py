import os
import uuid
import shutil
import logging

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Document
from exceptions import DocumentNotFoundError, InvalidFileTypeError, ProcessingError
from services.docling_service import DoclingService
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from api.websocket import send_processing_update

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentService:
    """Handles document CRUD operations and the background processing pipeline."""

    def __init__(self) -> None:
        self._docling = DoclingService()
        self._llm = LLMService()
        self._embedding = EmbeddingService()

    # ------------------------------------------------------------------
    # Upload & persistence
    # ------------------------------------------------------------------

    async def create_document(self, file: UploadFile, db: AsyncSession) -> Document:
        """Validate, persist, and register a single uploaded PDF.

        Raises:
            InvalidFileTypeError: if the file is not a PDF.
        """
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise InvalidFileTypeError(
                f"Only PDF files are accepted. Got: {file.filename}"
            )

        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}.pdf"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        doc = Document(
            id=doc_id,
            filename=safe_filename,
            original_filename=file.filename,
            file_path=file_path,
            status="pending",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_documents(self, db: AsyncSession) -> list[Document]:
        """Return all documents ordered by upload date descending."""
        result = await db.execute(
            select(Document).order_by(Document.upload_date.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, document_id: str, db: AsyncSession) -> Document:
        """Fetch a single document by ID.

        Raises:
            DocumentNotFoundError: if no document with *document_id* exists.
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise DocumentNotFoundError(f"Document not found: {document_id}")
        return doc

    async def delete_document(self, document_id: str, db: AsyncSession) -> None:
        """Delete a document and its associated file.

        Raises:
            DocumentNotFoundError: if no document with *document_id* exists.
        """
        doc = await self.get_document(document_id, db)

        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        await db.delete(doc)
        await db.commit()

    # ------------------------------------------------------------------
    # Background processing pipeline
    # ------------------------------------------------------------------

    async def process_document(self, document_id: str, file_path: str) -> None:
        """Background task: PDF → markdown → LLM extraction → chunk + embed.

        Transitions the document through ``processing`` → ``completed`` or
        ``failed``.  Uses its own database session so it can run independently
        of the request that scheduled it.
        """
        from database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                logger.warning("process_document: document %s not found", document_id)
                return

            try:
                doc.status = "processing"
                await db.commit()

                # Stage 1: Docling processing
                await send_processing_update(document_id, "docling_started")
                markdown, images = await self._docling.convert(file_path)
                doc.markdown_content = markdown
                doc.images = images
                await db.commit()
                await send_processing_update(document_id, "docling_completed", {
                    "markdown_length": len(markdown),
                    "images_count": len(images)
                })

                # Stage 2: LLM extraction
                await send_processing_update(document_id, "llm_extraction_started")
                extracted = await self._llm.extract_medical_fields(markdown)
                doc.extracted_data = extracted
                await db.commit()
                await send_processing_update(document_id, "llm_extraction_completed", {
                    "extracted_fields": extracted
                })

                # Stage 3: Embedding
                await send_processing_update(document_id, "embedding_started")
                await self._embedding.chunk_and_embed_document(db, document_id, markdown)
                await send_processing_update(document_id, "embedding_completed")

                doc.status = "completed"
                await db.commit()
                await send_processing_update(document_id, "processing_completed")

            except Exception as exc:
                logger.error(
                    "Processing failed for document %s: %s", document_id, exc
                )
                doc.status = "failed"
                doc.error_message = str(exc)
                await db.commit()
                await send_processing_update(document_id, "processing_failed", {
                    "error": str(exc)
                })

    def schedule_processing(
        self,
        background_tasks: BackgroundTasks,
        document_id: str,
        file_path: str,
    ) -> None:
        """Register the processing pipeline as a FastAPI background task."""
        background_tasks.add_task(self.process_document, document_id, file_path)
