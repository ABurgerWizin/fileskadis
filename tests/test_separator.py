"""Tests for the separator module."""

import pytest

from fileskadis.core.separator import parse_page_range


class TestParsePageRange:
    def test_single_page(self):
        assert parse_page_range("5", 10) == [4]

    def test_page_range(self):
        assert parse_page_range("1-3", 10) == [0, 1, 2]

    def test_multiple_ranges(self):
        assert parse_page_range("1-2, 5, 8-10", 10) == [0, 1, 4, 7, 8, 9]

    def test_out_of_range_ignored(self):
        assert parse_page_range("1, 100", 10) == [0]

    def test_invalid_format_ignored(self):
        assert parse_page_range("1, abc, 3", 10) == [0, 2]

    def test_empty_string(self):
        assert parse_page_range("", 10) == []

    def test_spaces_handled(self):
        assert parse_page_range(" 1 - 3 , 5 ", 10) == [0, 1, 2, 4]

    def test_duplicates_removed(self):
        result = parse_page_range("1, 1, 1-2", 10)
        assert result == [0, 1]

