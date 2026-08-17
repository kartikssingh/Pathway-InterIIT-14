from __future__ import annotations

import pytest

from fraudguard import similarity


class TestNormalise:
    def test_collapses_whitespace_and_case(self):
        assert similarity.normalise("  Hello\n\tWORLD  ") == "hello world"

    def test_handles_none(self):
        assert similarity.normalise(None) == ""


class TestTextSimilarity:
    def test_identical_text_is_one(self):
        text = "Businessman charged with laundering funds through shell companies."
        assert similarity.text_similarity(text, text) == 1.0

    def test_identical_up_to_whitespace_is_one(self):
        assert similarity.text_similarity("A B  c", "a b\nC") == 1.0

    def test_empty_input_is_zero(self):
        assert similarity.text_similarity("", "anything") == 0.0
        assert similarity.text_similarity(None, None) == 0.0

    def test_unrelated_text_is_low(self):
        left = "The company opened a new factory in Pune employing four hundred people."
        right = "Regulators fined the trader for market manipulation and insider dealing."
        assert similarity.text_similarity(left, right) < 0.3

    def test_related_text_is_high(self):
        left = "Regulators fined the trader for market manipulation and insider dealing."
        right = "The trader was fined by regulators over market manipulation allegations."
        assert similarity.text_similarity(left, right) > 0.3

    def test_result_is_bounded(self):
        score = similarity.text_similarity("alpha beta gamma", "beta gamma delta")
        assert 0.0 <= score <= 1.0

    def test_pure_python_matches_sklearn_direction(self):
        """The fallback must rank the same pairs the same way."""
        near = ("fraud investigation opened", "investigation into fraud opened")
        far = ("fraud investigation opened", "new bakery opens downtown")
        assert similarity._pure_python_similarity(*near) > similarity._pure_python_similarity(*far)


class TestJaccard:
    def test_disjoint_is_zero(self):
        assert similarity.jaccard("alpha beta", "gamma delta") == 0.0

    def test_identical_is_one(self):
        assert similarity.jaccard("alpha beta", "beta alpha") == 1.0

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_is_zero(self, value):
        assert similarity.jaccard(value, "alpha") == 0.0
