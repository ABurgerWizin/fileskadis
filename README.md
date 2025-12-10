# fileskadis

A Python library for efficient file operations on PDFs and images.

## Features

- **Aggregator**: Merge multiple PDFs and images into a single PDF
- **Separator**: Extract specific pages from PDFs
- **Masker**: Apply irreversible redactions (blur or solid color) to PDF regions

## Installation

```bash
# Using PDM
pdm install

# For development
pdm install -G dev
```

## Usage

### As a Library

```python
from fileskadis.core import Aggregator, Separator, Masker

# Aggregate files
aggregator = Aggregator()
aggregator.merge(["doc1.pdf", "image.png", "doc2.pdf"], "output.pdf")

# Separate pages
separator = Separator()
separator.extract("input.pdf", "1-3,5,7-10", "output_dir/")

# Mask regions
masker = Masker()
masker.redact("input.pdf", page=1, regions=[(100, 100, 200, 50)], output="redacted.pdf")
```

### Local UI Application

```bash
# Run the Gradio UI
make ui

# Or directly
pdm run fileskadis-ui
```

## Development

```bash
# Setup
make dev

# Run tests
make test

# Lint and format
make lint
make format

# Build
make build
```

## License

Apache-2.0

