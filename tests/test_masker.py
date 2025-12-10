"""Tests for the masker module."""

import pytest
from PIL import Image

from fileskadis.core.masker import Masker, Region


class TestRegion:
    def test_box_property(self):
        r = Region(x=10, y=20, width=100, height=50)
        assert r.box == (10, 20, 110, 70)

    def test_zero_region(self):
        r = Region(x=0, y=0, width=0, height=0)
        assert r.box == (0, 0, 0, 0)


class TestMasker:
    def test_init_defaults(self):
        m = Masker()
        assert m.render_scale == 2.0
        assert m.blur_radius == 30

    def test_init_custom(self):
        m = Masker(render_scale=1.5, blur_radius=20)
        assert m.render_scale == 1.5
        assert m.blur_radius == 20

    def test_apply_masks_blur(self):
        m = Masker()
        img = Image.new("RGB", (200, 200), "white")
        regions = [Region(x=50, y=50, width=100, height=100)]

        result = m._apply_masks(img, regions, "blur")

        assert result.size == img.size
        assert isinstance(result, Image.Image)

    def test_apply_masks_black(self):
        m = Masker()
        img = Image.new("RGB", (200, 200), "white")
        regions = [Region(x=50, y=50, width=100, height=100)]

        result = m._apply_masks(img, regions, "black")

        center_pixel = result.getpixel((100, 100))
        assert center_pixel == (0, 0, 0)

    def test_apply_masks_white(self):
        m = Masker()
        img = Image.new("RGB", (200, 200), "black")
        regions = [Region(x=50, y=50, width=100, height=100)]

        result = m._apply_masks(img, regions, "white")

        center_pixel = result.getpixel((100, 100))
        assert center_pixel == (255, 255, 255)

