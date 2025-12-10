"""PDF masking/redaction module."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter

from fileskadis.core.utils import get_logger, validate_pdf

log = get_logger(__name__)


@dataclass
class Region:
    """A rectangular region for masking (in image pixel coordinates)."""

    x: int
    y: int
    width: int
    height: int

    @property
    def box(self) -> tuple[int, int, int, int]:
        """Return (left, top, right, bottom) tuple."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


MaskType = Literal["blur", "black", "white"]


class Masker:
    """Apply irreversible redactions to PDF pages."""

    def __init__(self, render_scale: float = 2.0, blur_radius: int = 30):
        self.render_scale = render_scale
        self.blur_radius = blur_radius

    def redact(
        self,
        pdf_path: Union[str, Path],
        page_regions: dict[int, list[Region]],
        output_path: Union[str, Path],
        mask_type: MaskType = "blur",
    ) -> Path:
        """
        Apply redactions to PDF pages.

        Args:
            pdf_path: Source PDF path
            page_regions: Dict mapping page numbers (1-indexed) to list of Regions
            output_path: Output PDF path
            mask_type: Type of mask ("blur", "black", "white")

        Returns:
            Path to redacted PDF
        """
        pdf_path = validate_pdf(pdf_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf = pdfium.PdfDocument(pdf_path)
        page_count = len(pdf)

        log.info(
            "redacting_pdf",
            source=pdf_path.name,
            pages_affected=len(page_regions),
            mask_type=mask_type,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            page_images = []

            for page_idx in range(page_count):
                page_num = page_idx + 1
                bitmap = pdf[page_idx].render(scale=self.render_scale)
                img = bitmap.to_pil()

                if page_num in page_regions:
                    regions = page_regions[page_num]
                    img = self._apply_masks(img, regions, mask_type)
                    log.debug("page_masked", page=page_num, regions=len(regions))

                page_images.append(img)

            pdf.close()
            self._images_to_pdf(page_images, output_path)

        log.info("redaction_complete", output=str(output_path))
        return output_path

    def redact_page(
        self,
        pdf_path: Union[str, Path],
        page_num: int,
        regions: list[Region],
        output_path: Union[str, Path],
        mask_type: MaskType = "blur",
    ) -> Path:
        """
        Convenience method to redact a single page.

        Args:
            pdf_path: Source PDF path
            page_num: Page number (1-indexed)
            regions: List of regions to mask
            output_path: Output PDF path
            mask_type: Type of mask

        Returns:
            Path to redacted PDF
        """
        return self.redact(pdf_path, {page_num: regions}, output_path, mask_type)

    def _apply_masks(
        self,
        img: Image.Image,
        regions: list[Region],
        mask_type: MaskType,
    ) -> Image.Image:
        """Apply mask to image regions."""
        result = img.copy()

        for region in regions:
            box = region.box
            box = (
                max(0, box[0]),
                max(0, box[1]),
                min(img.width, box[2]),
                min(img.height, box[3]),
            )

            if box[2] <= box[0] or box[3] <= box[1]:
                continue

            if mask_type == "blur":
                cropped = result.crop(box)
                blurred = cropped.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))
                result.paste(blurred, box)
            else:
                draw = ImageDraw.Draw(result)
                color = "black" if mask_type == "black" else "white"
                draw.rectangle(box, fill=color)

        return result

    def _images_to_pdf(self, images: list[Image.Image], output: Path) -> None:
        """Convert list of images to PDF."""
        if not images:
            raise ValueError("No images to convert")

        rgb_images = []
        for img in images:
            if img.mode != "RGB":
                img = img.convert("RGB")
            rgb_images.append(img)

        rgb_images[0].save(
            output,
            "PDF",
            save_all=True,
            append_images=rgb_images[1:] if len(rgb_images) > 1 else [],
            resolution=150,
        )

    def preview_page(
        self,
        pdf_path: Union[str, Path],
        page_num: int,
        regions: list[Region] | None = None,
        mask_type: MaskType = "blur",
        scale: float = 1.0,
    ) -> Image.Image:
        """
        Generate preview of a page with optional masking.

        Args:
            pdf_path: PDF file path
            page_num: Page number (1-indexed)
            regions: Optional regions to mask
            mask_type: Type of mask
            scale: Preview scale

        Returns:
            PIL Image preview
        """
        pdf_path = validate_pdf(pdf_path)
        pdf = pdfium.PdfDocument(pdf_path)

        if page_num < 1 or page_num > len(pdf):
            pdf.close()
            raise ValueError(f"Page {page_num} out of range")

        bitmap = pdf[page_num - 1].render(scale=self.render_scale * scale)
        img = bitmap.to_pil()
        pdf.close()

        if regions:
            scaled_regions = [
                Region(
                    int(r.x * scale),
                    int(r.y * scale),
                    int(r.width * scale),
                    int(r.height * scale),
                )
                for r in regions
            ]
            img = self._apply_masks(img, scaled_regions, mask_type)

        return img

    def get_page_size(self, pdf_path: Union[str, Path], page_num: int) -> tuple[int, int]:
        """
        Get rendered page dimensions at current scale.

        Returns:
            (width, height) tuple in pixels
        """
        pdf_path = validate_pdf(pdf_path)
        pdf = pdfium.PdfDocument(pdf_path)

        if page_num < 1 or page_num > len(pdf):
            pdf.close()
            raise ValueError(f"Page {page_num} out of range")

        page = pdf[page_num - 1]
        width = int(page.get_width() * self.render_scale)
        height = int(page.get_height() * self.render_scale)
        pdf.close()
        return width, height

