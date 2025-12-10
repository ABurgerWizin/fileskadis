"""PDF page separation module."""

import re
from pathlib import Path
from typing import Union

import pypdfium2 as pdfium
from PIL import Image

from fileskadis.core.utils import get_logger, validate_pdf

log = get_logger(__name__)


def parse_page_range(range_str: str, max_pages: int) -> list[int]:
    """
    Parse a page range string into list of 0-indexed page numbers.

    Args:
        range_str: Range like "1-3, 5, 7-10" (1-indexed, inclusive)
        max_pages: Maximum number of pages in the document

    Returns:
        List of 0-indexed page numbers
    """
    pages = set()
    parts = [p.strip() for p in range_str.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            match = re.match(r"(\d+)\s*-\s*(\d+)", part)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                for i in range(start, end + 1):
                    if 1 <= i <= max_pages:
                        pages.add(i - 1)
        else:
            try:
                page = int(part)
                if 1 <= page <= max_pages:
                    pages.add(page - 1)
            except ValueError:
                continue

    return sorted(pages)


class Separator:
    """Extract and separate pages from PDFs."""

    def __init__(self, output_dpi: int = 150):
        self.output_dpi = output_dpi

    def extract(
        self,
        pdf_path: Union[str, Path],
        page_range: str,
        output_dir: Union[str, Path],
        as_images: bool = False,
    ) -> list[Path]:
        """
        Extract pages from a PDF.

        Args:
            pdf_path: Source PDF path
            page_range: Page range string (e.g., "1-3, 5, 7-10")
            output_dir: Output directory
            as_images: If True, export as images; otherwise as PDF

        Returns:
            List of created file paths
        """
        pdf_path = validate_pdf(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        pdf = pdfium.PdfDocument(pdf_path)
        page_count = len(pdf)
        pages = parse_page_range(page_range, page_count)

        if not pages:
            pdf.close()
            raise ValueError(f"No valid pages in range '{page_range}' (document has {page_count} pages)")

        log.info("extracting_pages", source=pdf_path.name, pages=len(pages), as_images=as_images)

        outputs = []
        stem = pdf_path.stem

        for page_idx in pages:
            page_num = page_idx + 1

            if as_images:
                output_file = output_dir / f"{stem}_page{page_num}.png"
                bitmap = pdf[page_idx].render(scale=self.output_dpi / 72)
                img = bitmap.to_pil()
                img.save(output_file, "PNG")
            else:
                output_file = output_dir / f"{stem}_page{page_num}.pdf"
                new_pdf = pdfium.PdfDocument.new()
                new_pdf.import_pages(pdf, [page_idx])
                new_pdf.save(output_file)
                new_pdf.close()

            outputs.append(output_file)
            log.debug("page_extracted", page=page_num, output=output_file.name)

        pdf.close()
        log.info("extraction_complete", count=len(outputs))
        return outputs

    def extract_single(
        self,
        pdf_path: Union[str, Path],
        page_range: str,
        output_path: Union[str, Path],
    ) -> Path:
        """
        Extract pages into a single PDF file.

        Args:
            pdf_path: Source PDF path
            page_range: Page range string
            output_path: Output PDF path

        Returns:
            Path to created PDF
        """
        pdf_path = validate_pdf(pdf_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf = pdfium.PdfDocument(pdf_path)
        page_count = len(pdf)
        pages = parse_page_range(page_range, page_count)

        if not pages:
            pdf.close()
            raise ValueError(f"No valid pages in range '{page_range}'")

        log.info("extracting_to_single", source=pdf_path.name, pages=len(pages))

        new_pdf = pdfium.PdfDocument.new()
        new_pdf.import_pages(pdf, pages)
        new_pdf.save(output_path)
        new_pdf.close()
        pdf.close()

        log.info("extraction_complete", output=str(output_path))
        return output_path

    def get_page_count(self, pdf_path: Union[str, Path]) -> int:
        """Get number of pages in a PDF."""
        pdf_path = validate_pdf(pdf_path)
        pdf = pdfium.PdfDocument(pdf_path)
        count = len(pdf)
        pdf.close()
        return count

    def render_page(
        self,
        pdf_path: Union[str, Path],
        page_num: int,
        scale: float = 1.0,
    ) -> Image.Image:
        """
        Render a single page as an image.

        Args:
            pdf_path: PDF file path
            page_num: Page number (1-indexed)
            scale: Render scale

        Returns:
            PIL Image of the page
        """
        pdf_path = validate_pdf(pdf_path)
        pdf = pdfium.PdfDocument(pdf_path)

        if page_num < 1 or page_num > len(pdf):
            pdf.close()
            raise ValueError(f"Page {page_num} out of range (1-{len(pdf)})")

        bitmap = pdf[page_num - 1].render(scale=scale)
        img = bitmap.to_pil()
        pdf.close()
        return img

