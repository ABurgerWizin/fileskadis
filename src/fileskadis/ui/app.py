"""Gradio UI application for fileskadis."""

import tempfile
from pathlib import Path

import gradio as gr
from PIL import Image, ImageDraw

from fileskadis.core.aggregator import Aggregator
from fileskadis.core.masker import Masker, Region
from fileskadis.core.separator import Separator


class FileskadisApp:
    """Main application class managing state and UI."""

    def __init__(self):
        self.aggregator = Aggregator()
        self.separator = Separator()
        self.masker = Masker()
        self.temp_dir = tempfile.mkdtemp()
        self._current_pdf: Path | None = None
        self._current_page: int = 1
        self._regions: list[Region] = []
        self._base_image: Image.Image | None = None
        self._click_start: tuple[int, int] | None = None

    def aggregate_files(
        self, files: list[str] | None
    ) -> tuple[str | None, list[Image.Image] | None]:
        """Aggregate uploaded files into a single PDF."""
        if not files:
            return None, None

        output_path = Path(self.temp_dir) / "aggregated.pdf"
        self.aggregator.merge(files, output_path)
        previews = self.aggregator.preview(files, scale=0.3)
        return str(output_path), previews

    def separate_pages(
        self,
        pdf_file: str | None,
        page_range: str,
        as_single: bool,
    ) -> tuple[str | None, str]:
        """Separate pages from PDF."""
        if not pdf_file or not page_range.strip():
            return None, "Please upload a PDF and specify page range"

        try:
            if as_single:
                output_path = Path(self.temp_dir) / "separated.pdf"
                self.separator.extract_single(pdf_file, page_range, output_path)
                return str(output_path), f"Created: {output_path.name}"
            else:
                output_dir = Path(self.temp_dir) / "separated"
                output_dir.mkdir(exist_ok=True)
                outputs = self.separator.extract(pdf_file, page_range, output_dir)
                import shutil

                zip_path = Path(self.temp_dir) / "separated_pages.zip"
                shutil.make_archive(str(zip_path.with_suffix("")), "zip", output_dir)
                return str(zip_path), f"Extracted {len(outputs)} pages"
        except Exception as e:
            return None, f"Error: {e}"

    def get_pdf_info(self, pdf_file: str | None) -> str:
        """Get page count info for uploaded PDF."""
        if not pdf_file:
            return "No PDF uploaded"
        try:
            count = self.separator.get_page_count(pdf_file)
            return f"Pages: {count}"
        except Exception as e:
            return f"Error: {e}"

    def load_mask_pdf(
        self, pdf_file: str | None
    ) -> tuple[Image.Image | None, str, int, str]:
        """Load PDF for masking and return first page preview."""
        if not pdf_file:
            return None, "No PDF uploaded", 1, ""

        self._current_pdf = Path(pdf_file)
        self._current_page = 1
        self._regions = []
        self._click_start = None

        try:
            count = self.separator.get_page_count(pdf_file)
            img = self.masker.preview_page(pdf_file, 1, scale=1.0)
            self._base_image = img.copy()
            return img, f"Page 1/{count} — Click to draw rectangles", count, ""
        except Exception as e:
            return None, f"Error: {e}", 1, ""

    def change_mask_page(
        self, pdf_file: str | None, page_num: int
    ) -> tuple[Image.Image | None, str, str]:
        """Change current page for masking."""
        if not pdf_file:
            return None, "No PDF", ""

        self._current_page = int(page_num)
        self._regions = []
        self._click_start = None

        try:
            count = self.separator.get_page_count(pdf_file)
            img = self.masker.preview_page(pdf_file, self._current_page, scale=1.0)
            self._base_image = img.copy()
            return img, f"Page {self._current_page}/{count} — Click to draw rectangles", ""
        except Exception as e:
            return None, f"Error: {e}", ""

    def _draw_regions_on_image(self, mask_type: str = "blur") -> Image.Image | None:
        """Draw current regions on the base image."""
        if self._base_image is None:
            return None

        img = self._base_image.copy()

        if self._regions:
            img = self.masker._apply_masks(img, self._regions, mask_type)  # type: ignore

        draw = ImageDraw.Draw(img)
        for i, region in enumerate(self._regions):
            box = region.box
            draw.rectangle(box, outline="#ff3366", width=3)
            draw.text((box[0] + 5, box[1] + 5), f"{i + 1}", fill="#ff3366")

        if self._click_start:
            x, y = self._click_start
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill="#00ff88", outline="#ffffff")

        return img

    def _format_regions_text(self) -> str:
        """Format regions list as text."""
        if not self._regions:
            return ""
        lines = []
        for i, r in enumerate(self._regions):
            lines.append(f"{i + 1}. ({r.x}, {r.y}) → {r.width}×{r.height}")
        return "\n".join(lines)

    def handle_image_click(
        self,
        pdf_file: str | None,
        mask_type: str,
        evt: gr.SelectData,
    ) -> tuple[Image.Image | None, str, str]:
        """Handle click on image to define rectangle corners."""
        if not pdf_file or self._base_image is None:
            return None, "Load a PDF first", ""

        x, y = int(evt.index[0]), int(evt.index[1])

        if self._click_start is None:
            self._click_start = (x, y)
            img = self._draw_regions_on_image(mask_type)
            return img, f"First corner set at ({x}, {y}). Click second corner.", self._format_regions_text()
        else:
            x1, y1 = self._click_start
            x2, y2 = x, y

            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            if width > 5 and height > 5:
                self._regions.append(Region(x=left, y=top, width=width, height=height))

            self._click_start = None
            img = self._draw_regions_on_image(mask_type)
            return img, f"{len(self._regions)} region(s) selected", self._format_regions_text()

    def remove_last_region(
        self, pdf_file: str | None, mask_type: str
    ) -> tuple[Image.Image | None, str, str]:
        """Remove the last added region."""
        if self._regions:
            self._regions.pop()
        self._click_start = None

        if pdf_file and self._base_image:
            img = self._draw_regions_on_image(mask_type)
            return img, f"{len(self._regions)} region(s)", self._format_regions_text()
        return None, "No regions", ""

    def clear_regions(
        self, pdf_file: str | None, mask_type: str
    ) -> tuple[Image.Image | None, str, str]:
        """Clear all selected regions."""
        self._regions = []
        self._click_start = None

        if pdf_file and self._base_image:
            img = self._draw_regions_on_image(mask_type)
            return img, "Cleared", ""
        return None, "Cleared", ""

    def update_preview(
        self, pdf_file: str | None, mask_type: str
    ) -> tuple[Image.Image | None, str]:
        """Update preview when mask type changes."""
        if pdf_file and self._base_image:
            img = self._draw_regions_on_image(mask_type)
            return img, f"{len(self._regions)} region(s)"
        return None, ""

    def apply_mask(
        self,
        pdf_file: str | None,
        mask_type: str,
    ) -> tuple[str | None, str]:
        """Apply mask and export PDF."""
        if not pdf_file:
            return None, "No PDF loaded"
        if not self._regions:
            return None, "No regions selected — click on image to draw rectangles"

        try:
            output_path = Path(self.temp_dir) / "masked.pdf"
            self.masker.redact(
                pdf_file,
                {self._current_page: self._regions},
                output_path,
                mask_type=mask_type,  # type: ignore
            )
            return str(output_path), f"Created masked PDF with {len(self._regions)} redaction(s)"
        except Exception as e:
            return None, f"Error: {e}"


def create_ui() -> gr.Blocks:
    """Create the Gradio interface."""
    app = FileskadisApp()

    with gr.Blocks(title="fileskadis") as demo:
        gr.Markdown(
            """
            # fileskadis
            **PDF & Image Operations** — Aggregate, Separate, Mask
            """
        )

        with gr.Tabs():
            with gr.Tab("Aggregate"):
                gr.Markdown("Merge multiple PDFs and images into a single PDF file.")
                with gr.Row():
                    with gr.Column(scale=1):
                        agg_files = gr.File(
                            label="Upload Files",
                            file_count="multiple",
                            file_types=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"],
                        )
                        agg_btn = gr.Button("Merge Files", variant="primary", size="lg")
                        agg_download = gr.File(label="Download Merged PDF")
                    with gr.Column(scale=2):
                        agg_preview = gr.Gallery(
                            label="Preview",
                            columns=3,
                            height=500,
                            object_fit="contain",
                        )

                agg_btn.click(
                    fn=app.aggregate_files,
                    inputs=[agg_files],
                    outputs=[agg_download, agg_preview],
                )

            with gr.Tab("Separate"):
                gr.Markdown("Extract specific pages from a PDF document.")
                with gr.Row():
                    with gr.Column(scale=1):
                        sep_file = gr.File(
                            label="Upload PDF",
                            file_count="single",
                            file_types=[".pdf"],
                        )
                        sep_info = gr.Textbox(label="Document Info", interactive=False)
                        sep_range = gr.Textbox(
                            label="Page Range",
                            placeholder="e.g., 1-3, 5, 7-10",
                            info="Comma-separated ranges, 1-indexed",
                        )
                        sep_single = gr.Checkbox(
                            label="Output as single PDF",
                            value=True,
                            info="Uncheck to get individual pages as ZIP",
                        )
                        sep_btn = gr.Button("Extract Pages", variant="primary", size="lg")
                        sep_download = gr.File(label="Download")
                        sep_status = gr.Textbox(label="Status", interactive=False)

                sep_file.change(
                    fn=app.get_pdf_info,
                    inputs=[sep_file],
                    outputs=[sep_info],
                )
                sep_btn.click(
                    fn=app.separate_pages,
                    inputs=[sep_file, sep_range, sep_single],
                    outputs=[sep_download, sep_status],
                )

            with gr.Tab("Mask / Redact"):
                gr.Markdown(
                    """
                    Apply irreversible redactions to PDF regions.
                    **Click on the image** to set rectangle corners (2 clicks = 1 rectangle).
                    """
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        mask_file = gr.File(
                            label="Upload PDF",
                            file_count="single",
                            file_types=[".pdf"],
                        )
                        mask_info = gr.Textbox(label="Info", interactive=False)
                        mask_page = gr.Slider(
                            minimum=1,
                            maximum=100,
                            step=1,
                            value=1,
                            label="Page",
                        )
                        mask_type = gr.Radio(
                            choices=["blur", "black", "white"],
                            value="blur",
                            label="Mask Type",
                        )
                        mask_regions = gr.Textbox(
                            label="Selected Regions",
                            interactive=False,
                            lines=5,
                            placeholder="Regions will appear here...",
                        )
                        with gr.Row():
                            mask_undo_btn = gr.Button("Undo Last", size="sm")
                            mask_clear_btn = gr.Button("Clear All", size="sm")
                        mask_apply_btn = gr.Button("Apply Mask & Export", variant="primary", size="lg")
                        mask_download = gr.File(label="Download Masked PDF")
                        mask_status = gr.Textbox(label="Status", interactive=False)

                    with gr.Column(scale=2):
                        mask_preview = gr.Image(
                            label="Click to select regions",
                            type="pil",
                            interactive=True,
                            height=700,
                        )

                mask_file.change(
                    fn=app.load_mask_pdf,
                    inputs=[mask_file],
                    outputs=[mask_preview, mask_info, mask_page, mask_regions],
                )

                mask_page.change(
                    fn=app.change_mask_page,
                    inputs=[mask_file, mask_page],
                    outputs=[mask_preview, mask_info, mask_regions],
                )

                mask_preview.select(
                    fn=app.handle_image_click,
                    inputs=[mask_file, mask_type],
                    outputs=[mask_preview, mask_status, mask_regions],
                )

                mask_type.change(
                    fn=app.update_preview,
                    inputs=[mask_file, mask_type],
                    outputs=[mask_preview, mask_status],
                )

                mask_undo_btn.click(
                    fn=app.remove_last_region,
                    inputs=[mask_file, mask_type],
                    outputs=[mask_preview, mask_status, mask_regions],
                )

                mask_clear_btn.click(
                    fn=app.clear_regions,
                    inputs=[mask_file, mask_type],
                    outputs=[mask_preview, mask_status, mask_regions],
                )

                mask_apply_btn.click(
                    fn=app.apply_mask,
                    inputs=[mask_file, mask_type],
                    outputs=[mask_download, mask_status],
                )

        gr.Markdown("<center>fileskadis v0.1.0</center>")

    return demo


THEME = gr.themes.Base(
    primary_hue="stone",
    secondary_hue="neutral",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("IBM Plex Sans"),
    font_mono=gr.themes.GoogleFont("IBM Plex Mono"),
).set(
    body_background_fill="#0f0f0f",
    body_background_fill_dark="#0f0f0f",
    body_text_color="#e4e4e7",
    body_text_color_dark="#e4e4e7",
    button_primary_background_fill="#3f3f46",
    button_primary_background_fill_hover="#52525b",
    button_primary_text_color="#fafafa",
    block_background_fill="#18181b",
    block_background_fill_dark="#18181b",
    block_border_color="#27272a",
    block_label_text_color="#a1a1aa",
    input_background_fill="#27272a",
    input_background_fill_dark="#27272a",
    input_border_color="#3f3f46",
)

CSS = """
.container { max-width: 1400px; margin: auto; }
footer { text-align: center; color: #71717a; padding: 1rem; }
"""


def main():
    """Entry point for the UI application."""
    demo = create_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=False,
        theme=THEME,
        css=CSS,
    )


if __name__ == "__main__":
    main()
