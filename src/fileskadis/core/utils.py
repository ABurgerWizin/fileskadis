"""Shared utilities for fileskadis."""

from pathlib import Path
from typing import Union

import structlog

SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
SUPPORTED_PDF_FORMATS = {".pdf"}
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS | SUPPORTED_PDF_FORMATS


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


def validate_file(path: Union[str, Path]) -> Path:
    """Validate a single file path and return Path object."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if not p.is_file():
        raise ValueError(f"Not a file: {p}")
    if p.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {p.suffix}")
    return p


def validate_pdf(path: Union[str, Path]) -> Path:
    """Validate a PDF file path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if not p.is_file():
        raise ValueError(f"Not a file: {p}")
    if p.suffix.lower() not in SUPPORTED_PDF_FORMATS:
        raise ValueError(f"Not a PDF file: {p}")
    return p


def is_image(path: Path) -> bool:
    """Check if path is a supported image file."""
    return path.suffix.lower() in SUPPORTED_IMAGE_FORMATS


def is_pdf(path: Path) -> bool:
    """Check if path is a PDF file."""
    return path.suffix.lower() in SUPPORTED_PDF_FORMATS

