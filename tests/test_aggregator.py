"""Tests for the aggregator module."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from fileskadis.core.aggregator import Aggregator


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_images(temp_dir):
    """Create sample test images."""
    images = []
    for i, color in enumerate(["red", "green", "blue"]):
        path = temp_dir / f"test_{i}.png"
        img = Image.new("RGB", (100, 100), color)
        img.save(path)
        images.append(path)
    return images


class TestAggregator:
    def test_init_default_dpi(self):
        agg = Aggregator()
        assert agg.output_dpi == 300

    def test_init_custom_dpi(self):
        agg = Aggregator(output_dpi=150)
        assert agg.output_dpi == 150

    def test_merge_images(self, sample_images, temp_dir):
        agg = Aggregator()
        output = temp_dir / "output.pdf"
        result = agg.merge(sample_images, output)

        assert result.exists()
        assert result.suffix == ".pdf"

    def test_merge_empty_list_raises(self, temp_dir):
        agg = Aggregator()
        with pytest.raises(Exception):
            agg.merge([], temp_dir / "output.pdf")

    def test_preview_images(self, sample_images):
        agg = Aggregator()
        previews = agg.preview(sample_images, scale=0.5)

        assert len(previews) == 3
        for preview in previews:
            assert isinstance(preview, Image.Image)

