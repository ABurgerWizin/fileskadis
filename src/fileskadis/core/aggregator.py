"""PDF/Image aggregation module."""

import tempfile
from pathlib import Path
from typing import Union

import pypdfium2 as pdfium
from PIL import Image

from fileskadis.core.utils import get_logger, is_image, is_pdf, validate_file

log = get_logger(__name__)


class Aggregator:
    """Aggregate multiple PDFs and images into a single PDF."""

    def __init__(self, output_dpi: int = 300):
        self.output_dpi = output_dpi

    def merge(
        self,
        files: list[Union[str, Path]],
        output: Union[str, Path],
    ) -> Path:
        """
        Merge multiple files into a single PDF.

        Args:
            files: List of PDF/image file paths
            output: Output PDF path

        Returns:
            Path to the created PDF
        """
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        valid_files = [validate_file(f) for f in files]
        log.info("aggregating_files", count=len(valid_files), output=str(output_path))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pdf_parts = []

            for file_path in valid_files:
                if is_image(file_path):
                    pdf_parts.append(self._image_to_pdf(file_path, temp_path))
                elif is_pdf(file_path):
                    pdf_parts.append(file_path)

            self._merge_pdfs(pdf_parts, output_path)

        log.info("aggregation_complete", output=str(output_path))
        return output_path

    def _image_to_pdf(self, image_path: Path, temp_dir: Path) -> Path:
        """Convert image to temporary PDF."""
        with Image.open(image_path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            temp_pdf = temp_dir / f"{image_path.stem}.pdf"
            img.save(temp_pdf, "PDF", resolution=self.output_dpi, quality=95)
            log.debug("image_converted", image=image_path.name)
            return temp_pdf

    def _merge_pdfs(self, pdf_paths: list[Path], output: Path) -> None:
        """Merge multiple PDFs into one."""
        merged = pdfium.PdfDocument.new()

        for pdf_path in pdf_paths:
            src = pdfium.PdfDocument(pdf_path)
            page_count = len(src)
            merged.import_pages(src, list(range(page_count)))
            src.close()
            log.debug("pdf_merged", file=pdf_path.name, pages=page_count)

        merged.save(output)
        merged.close()

    def preview(self, files: list[Union[str, Path]], scale: float = 0.5) -> list[Image.Image]:
        """
        Generate preview images of what the merged PDF would look like.

        Args:
            files: List of PDF/image file paths
            scale: Scale factor for preview (default 0.5)

        Returns:
            List of PIL Images for preview
        """
        previews = []
        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                continue

            if is_image(path):
                with Image.open(path) as img:
                    w, h = int(img.width * scale), int(img.height * scale)
                    previews.append(img.resize((w, h), Image.Resampling.LANCZOS).copy())
            elif is_pdf(path):
                pdf = pdfium.PdfDocument(path)
                for page in pdf:
                    bitmap = page.render(scale=scale)
                    previews.append(bitmap.to_pil())
                pdf.close()

        return previews

