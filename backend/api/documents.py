from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import DocumentResponse
from exceptions import DocumentNotFoundError, InvalidFileTypeError
from services.document_service import DocumentService

router = APIRouter()
_document_service = DocumentService()


@router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    created_docs = []

    for file in files:
        try:
            doc = await _document_service.create_document(file, db)
        except InvalidFileTypeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        _document_service.schedule_processing(background_tasks, doc.id, doc.file_path)
        created_docs.append(doc)

    return created_docs


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    return await _document_service.list_documents(db)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await _document_service.get_document(document_id, db)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await _document_service.delete_document(document_id, db)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

