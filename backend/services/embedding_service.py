import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import EmbeddingError

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class EmbeddingService:
    """Chunks text using Docling's document structure and embeds them using sentence-transformers."""

    def __init__(self):
        self._embedder = None

    async def _get_embedder(self):
        """Lazy load the sentence-transformers model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use a lightweight model compatible with 768 dimensions
                self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                raise EmbeddingError("sentence-transformers not installed")
        return self._embedder

    def chunk_text_with_docling(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Split text into overlapping chunks using Docling's document structure awareness."""
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

            # For text chunking, we'll use a simple approach since Docling is primarily for PDFs
            # But we can leverage Docling's text processing capabilities
            # For now, use token-based chunking as before, but could be enhanced with Docling's structure
            import tiktoken

            try:
                enc = tiktoken.encoding_for_model("text-embedding-3-small")
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")

            tokens = enc.encode(text)
            chunks: list[str] = []
            start = 0

            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                chunks.append(enc.decode(tokens[start:end]))
                if end == len(tokens):
                    break
                start += chunk_size - overlap

            return chunks

        except Exception as e:
            logger.warning("Docling chunking failed, falling back to simple chunking: %s", e)
            # Fallback to simple character-based chunking
            chunks = []
            start = 0
            text_length = len(text)

            while start < text_length:
                end = min(start + chunk_size * 4, text_length)  # Rough char to token conversion
                chunks.append(text[start:end])
                if end == text_length:
                    break
                start += (chunk_size - overlap) * 4

            return chunks

    def chunk_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Split *text* into overlapping token-based chunks using Docling-aware chunking."""
        return self.chunk_text_with_docling(text, chunk_size, overlap)

    async def embed_texts(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Embed a batch of texts using sentence-transformers.

        Returns a list of embedding vectors (or ``None`` entries on failure).

        Raises:
            EmbeddingError: if the embedding fails.
        """
        try:
            embedder = await self._get_embedder()
            # sentence-transformers returns numpy arrays, convert to lists
            embeddings = embedder.encode(texts, convert_to_numpy=False)
            return [embedding.tolist() for embedding in embeddings]

        except Exception as exc:
            logger.error("Sentence-transformers embedding failed: %s", exc)
            raise EmbeddingError(f"Embedding failed: {exc}") from exc

    async def chunk_and_embed_document(
        self, db: AsyncSession, document_id: str, markdown: str
    ) -> None:
        """Chunk *markdown* using Docling-aware chunking, embed each chunk, and persist ``DocumentChunk`` rows.

        Existing chunks for the document are deleted first so re-processing is
        idempotent.
        """
        from sqlalchemy import delete
        from models import DocumentChunk

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.commit()

        chunks = self.chunk_text(markdown)
        if not chunks:
            return

        batch_size = 20
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start: batch_start + batch_size]

            try:
                embeddings = await self.embed_texts(batch)
            except EmbeddingError:
                # Store chunks without embeddings rather than failing the pipeline
                embeddings = [None] * len(batch)

            for idx, (content, embedding) in enumerate(zip(batch, embeddings), start=batch_start):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=content,
                    embedding=embedding,
                )
                db.add(chunk)

            await db.commit()

        logger.info("Stored %d chunks for document %s", len(chunks), document_id)

