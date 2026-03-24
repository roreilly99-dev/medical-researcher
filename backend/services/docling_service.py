import base64
import io
import logging

from exceptions import ProcessingError

logger = logging.getLogger(__name__)


class DoclingService:
    """Converts PDF files to markdown using PyMuPDF (lightweight alternative to Docling)."""

    async def convert(self, file_path: str) -> tuple[str, list[str]]:
        """Convert a PDF to markdown and extract embedded images as base64 strings.

        Returns:
            A (markdown_text, images_base64) tuple.

        Raises:
            ProcessingError: if PDF conversion fails.
        """
        images_b64: list[str] = []

        try:
            import pymupdf4llm
            import pymupdf

            # Convert PDF to markdown
            markdown = pymupdf4llm.to_markdown(file_path)

            # Extract images
            try:
                doc = pymupdf.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        try:
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            b64 = base64.b64encode(image_bytes).decode("utf-8")
                            images_b64.append(b64)
                        except Exception as img_err:
                            logger.debug("Could not extract image %d from page %d: %s", 
                                       img_index, page_num, img_err)
                doc.close()
            except Exception as img_err:
                logger.warning("Could not extract images: %s", img_err)

            return markdown, images_b64

        except Exception as exc:
            logger.error("PDF conversion failed for %s: %s", file_path, exc)
            raise ProcessingError(f"PDF conversion failed: {exc}") from exc
