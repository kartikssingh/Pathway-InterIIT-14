"""The deterministic scoring contract.

These lock down the arithmetic the compliance prompt asks the LLM to follow, so
a prompt edit that changes the algorithm without changing the code (or the
reverse) shows up as a failing test.
"""

from __future__ import annotations

import pytest

from fraudguard import scoring


class TestClamping:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0.5, 0.5),
            (-1, 0.0),
            (2, 1.0),
            (None, 0.0),
            ("not a number", 0.0),
            (float("nan"), 0.0),
            (float("inf"), 0.0),
        ],
    )
    def test_clamp01(self, value, expected):
        assert scoring.clamp01(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("85%", 0.85),
            (85, 0.85),
            (0.85, 0.85),
            ("0.85", 0.85),
            (None, 0.0),
            ("", 0.0),
        ],
    )
    def test_parse_confidence(self, value, expected):
        assert scoring.parse_confidence(value) == pytest.approx(expected)


class TestSanctionScore:
    def test_saturates_at_five_matches(self):
        assert scoring.sanction_score(5) == 1.0
        assert scoring.sanction_score(50) == 1.0

    def test_scales_linearly_below_saturation(self):
        assert scoring.sanction_score(1) == pytest.approx(0.2)
        assert scoring.sanction_score(3) == pytest.approx(0.6)

    def test_parses_counts_out_of_text(self):
        assert scoring.sanction_score("2 matches found") == pytest.approx(0.4)

    def test_no_matches_is_zero(self):
        assert scoring.sanction_score(None) == 0.0
        assert scoring.sanction_score("clean") == 0.0


class TestWebEvidence:
    def test_empty_evidence_is_zero(self):
        assert scoring.web_evidence_score([]) == 0.0

    def test_probabilistic_union(self):
        # 1 - (1-0.5)(1-0.5) = 0.75
        assert scoring.probabilistic_union([0.5, 0.5]) == pytest.approx(0.75)

    def test_severity_lookup_beats_inference(self):
        article = scoring.ArticleEvidence(
            authenticity=1.0, article_type="conviction", excerpt="totally unrelated words"
        )
        assert article.severity == 0.95

    def test_severity_inferred_from_text(self):
        article = scoring.ArticleEvidence(
            authenticity=1.0, title="Businessman convicted of laundering"
        )
        assert article.severity == scoring.SEVERITY_BY_TYPE["conviction"]

    def test_unknown_text_falls_back_to_other(self):
        article = scoring.ArticleEvidence(authenticity=1.0, title="Company opens new office")
        assert article.severity == scoring.SEVERITY_BY_TYPE["other"]


class TestClassification:
    @pytest.mark.parametrize(
        ("score", "band"),
        [
            (0.0, "LOW"),
            (0.249, "LOW"),
            (0.250, "MEDIUM"),
            (0.499, "MEDIUM"),
            (0.500, "HIGH"),
            (0.749, "HIGH"),
            (0.750, "CRITICAL"),
            (1.0, "CRITICAL"),
        ],
    )
    def test_band_boundaries(self, score, band):
        assert scoring.classify(score) == band


class TestAssessment:
    def test_clean_entity_scores_zero(self):
        result = scoring.assess(entity_name="Clean Person")
        assert result.risk_score == 0.0
        assert result.risk_classification == "LOW"
        assert result.match_found is False

    def test_weights_sum_correctly(self):
        # 5 sanctions (1.0) * 0.60 + no web (0.0) + full confidence (1.0) * 0.10
        result = scoring.assess(sanction_matches=5, match_confidence=1.0)
        assert result.risk_score == pytest.approx(0.70)
        assert result.risk_classification == "HIGH"
        assert result.strongest_driver == "sanctions"

    def test_web_evidence_contributes(self):
        articles = [
            scoring.ArticleEvidence(authenticity=1.0, article_type="official_sanction"),
            scoring.ArticleEvidence(authenticity=0.8, article_type="conviction"),
        ]
        result = scoring.assess(articles=articles)
        assert result.web_evidence_score == 1.0
        assert result.risk_score == pytest.approx(0.30)
        assert result.contributing_articles == 2

    def test_summary_mentions_the_formula(self):
        result = scoring.assess(sanction_matches=2, match_confidence=0.5)
        assert "final_risk_score" in result.summary
        assert result.risk_classification in result.summary

    def test_risk_json_shape_matches_the_prompt_contract(self):
        payload = scoring.assess(sanction_matches=1).to_risk_json()
        assert set(payload) == {"risk_score", "risk_classification", "match_found"}
        assert 0.0 <= payload["risk_score"] <= 1.0


class TestDeviation:
    def test_agreement_is_within_tolerance(self):
        reference = scoring.assess(sanction_matches=5, match_confidence=1.0)
        audit = scoring.deviation(
            {"risk_score": 0.70, "risk_classification": "HIGH"}, reference
        )
        assert audit["classification_agrees"] is True
        assert audit["within_tolerance"] is True
        assert audit["delta"] == pytest.approx(0.0)

    def test_large_disagreement_is_flagged(self):
        reference = scoring.assess(sanction_matches=5, match_confidence=1.0)
        audit = scoring.deviation(
            {"risk_score": 0.10, "risk_classification": "LOW"}, reference
        )
        assert audit["classification_agrees"] is False
        assert audit["within_tolerance"] is False


class TestRpsHelpers:
    @pytest.mark.parametrize(
        ("rps", "band"), [(0.0, "LOW"), (0.14, "LOW"), (0.15, "MEDIUM"), (0.30, "HIGH"), (0.99, "HIGH")]
    )
    def test_rps_bands(self, rps, band):
        assert scoring.rps_band(rps) == band

    def test_combine_independent_is_symmetric_and_monotonic(self):
        assert scoring.combine_independent(0.3, 0.5) == pytest.approx(
            scoring.combine_independent(0.5, 0.3)
        )
        assert scoring.combine_independent(0.3, 0.5) > 0.5

    def test_combining_with_zero_is_identity(self):
        assert scoring.combine_independent(0.42, 0.0) == pytest.approx(0.42)


class TestFallbackScale:
    def test_opensanctions_fallback_stays_in_zero_to_one(self):
        """Regression: the old fallback returned a 0-100 integer."""
        for raw in (0.0, 0.25, 0.9, 1.0):
            payload = scoring.from_opensanctions_score(raw).to_risk_json()
            assert 0.0 <= payload["risk_score"] <= 1.0
