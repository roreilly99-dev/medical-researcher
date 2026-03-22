from fastapi import APIRouter

from ingest.documents import process_dir
router = APIRouter()

@router.post("/ingest/")
async def ingest_with_docling(documents_dir):
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    documents_dir_list = process_dir(documents_dir)
    markdown = []
    for doc in documents_dir_list:
        converted_doc = converter.conver(doc).document
        document_markdown = converted_doc.export_to_markdown()
        markdown.append(document_markdown)

    print(markdown)
    return print("Data Ingested")
