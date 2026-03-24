import base64
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def convert_pdf_to_markdown(file_path: str) -> tuple[str, list[str]]:
    """Convert a PDF file to markdown using docling. Returns (markdown, images_base64)."""
    images_b64: list[str] = []

    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 1.0
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        result = converter.convert(file_path)
        markdown = result.document.export_to_markdown()

        try:
            for element, _level in result.document.iterate_items():
                if hasattr(element, "image") and element.image is not None:
                    pil_img = element.image.pil_image
                    if pil_img is not None:
                        buf = io.BytesIO()
                        pil_img.save(buf, format="PNG")
                        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                        images_b64.append(b64)
        except Exception as img_err:
            logger.warning("Could not extract images: %s", img_err)

        return markdown, images_b64

    except Exception as exc:
        logger.error("Docling conversion failed for %s: %s", file_path, exc)
        raise RuntimeError(f"PDF conversion failed: {exc}") from exc
