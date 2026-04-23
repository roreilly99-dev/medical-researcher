import base64
import io
import logging

from exceptions import ProcessingError

logger = logging.getLogger(__name__)


class DoclingService:
    """Converts PDF files to markdown using Docling with PaddleOCR."""

    async def convert(self, file_path: str) -> tuple[str, list[str]]:
        """Convert a PDF to markdown and extract embedded images as base64 strings.

        Returns:
            A (markdown_text, images_base64) tuple.

        Raises:
            ProcessingError: if PDF conversion fails.
        """
        images_b64: list[str] = []

        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            # Configure pipeline options with OCR (using default ONNX Runtime backend for better compatibility)
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = RapidOcrOptions()  # Uses ONNX Runtime by default

            # Create converter
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            # Convert the document
            result = doc_converter.convert(file_path)
            document = result.document

            # Export to markdown
            markdown = document.export_to_markdown()

            # Extract images
            for item in document.pictures:
                try:
                    # Get image data
                    image_data = item.image
                    if hasattr(image_data, 'pil_image'):
                        # Convert PIL image to bytes
                        img_byte_arr = io.BytesIO()
                        image_data.pil_image.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                    else:
                        # Assume it's bytes
                        img_bytes = image_data

                    # Encode to base64
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    images_b64.append(b64)
                except Exception as img_err:
                    logger.debug("Could not extract image: %s", img_err)

            return markdown, images_b64

        except Exception as exc:
            logger.error("PDF conversion failed for %s: %s", file_path, exc)
            raise ProcessingError(f"PDF conversion failed: {exc}") from exc
