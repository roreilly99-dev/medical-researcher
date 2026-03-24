import os
import uuid
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Document
from schemas import DocumentResponse
from services.docling_service import convert_pdf_to_markdown
from services.llm_service import extract_medical_fields
from services.embedding_service import chunk_and_embed_document

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()


async def process_document(document_id: str, file_path: str):
    """Background task: convert PDF → markdown → extract fields → embed chunks."""
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return

        try:
            doc.status = "processing"
            await db.commit()

            markdown, images = await convert_pdf_to_markdown(file_path)
            doc.markdown_content = markdown
            doc.images = images
            await db.commit()

            extracted = await extract_medical_fields(markdown)
            doc.extracted_data = extracted
            await db.commit()

            await chunk_and_embed_document(db, document_id, markdown)

            doc.status = "completed"
            await db.commit()

        except Exception as exc:
            doc.status = "failed"
            doc.error_message = str(exc)
            await db.commit()


@router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    created_docs = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files are accepted. Got: {file.filename}")

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

        background_tasks.add_task(process_document, doc_id, file_path)
        created_docs.append(doc)

    return created_docs


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.upload_date.desc()))
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.commit()
