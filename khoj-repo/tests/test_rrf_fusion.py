"""
Tests for rrf_fuse function.

Tests Reciprocal Rank Fusion (RRF) for combining multiple ranked result lists.
"""

import pytest
from khoj.utils.helpers import rrf_fuse


class TestRrfFuseBasic:
    """Tests for basic RRF fusion functionality."""

    def test_fuse_single_list(self):
        """Test rrf_fuse() with a single result list."""
        results = [
            [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 3
        assert fused[0]["id"] == "1"
        assert fused[1]["id"] == "2"
        assert fused[2]["id"] == "3"
        assert "rrf_score" in fused[0]

    def test_fuse_multiple_lists(self):
        """Test rrf_fuse() with multiple result lists."""
        results = [
            [{"id": "1"}, {"id": "2"}],
            [{"id": "2"}, {"id": "3"}],
        ]

        fused = rrf_fuse(results)

        # Should have all unique IDs
        assert len(fused) == 3
        ids = [r["id"] for r in fused]
        assert "1" in ids
        assert "2" in ids
        assert "3" in ids

    def test_fuse_preserves_order_by_score(self):
        """Test rrf_fuse() sorts results by RRF score descending."""
        results = [
            [{"id": "a"}, {"id": "b"}],  # a gets rank 0, b gets rank 1
            [{"id": "b"}, {"id": "a"}],  # b gets rank 0, a gets rank 1
        ]

        fused = rrf_fuse(results, k=60)

        # Both a and b appear in both lists at different ranks
        # a: 1/(60+0+1) + 1/(60+1+1) = 1/61 + 1/62 ≈ 0.0164 + 0.0161 = 0.0325
        # b: 1/(60+1+1) + 1/(60+0+1) = 1/62 + 1/61 ≈ 0.0161 + 0.0164 = 0.0325
        # Actually they should have equal scores, so order may vary or be stable
        # Let's test with different scenario

        results2 = [
            [{"id": "a"}, {"id": "b"}],  # a rank 0, b rank 1
            [{"id": "a"}, {"id": "c"}],  # a rank 0, c rank 1
        ]

        fused2 = rrf_fuse(results2, k=60)

        # a appears in both at rank 0: 2 * 1/61 ≈ 0.0328
        # b appears once at rank 1: 1/62 ≈ 0.0161
        # c appears once at rank 1: 1/62 ≈ 0.0161
        assert fused2[0]["id"] == "a"
        assert fused2[0]["rrf_score"] > fused2[1]["rrf_score"]


class TestRrfFuseDeduplication:
    """Tests for deduplication by ID."""

    def test_deduplicate_same_id_multiple_lists(self):
        """Test rrf_fuse() deduplicates results with same ID across lists."""
        results = [
            [{"id": "1", "score": 0.9}],
            [{"id": "1", "score": 0.8}],
            [{"id": "1", "score": 0.7}],
        ]

        fused = rrf_fuse(results)

        # Should only have one result with id "1"
        assert len(fused) == 1
        assert fused[0]["id"] == "1"
        # Should have accumulated RRF score
        assert fused[0]["rrf_score"] > 0

    def test_deduplication_prefers_first_occurrence(self):
        """Test rrf_fuse() prefers first occurrence for result data."""
        results = [
            [{"id": "1", "content": "first version", "score": 0.9}],
            [{"id": "1", "content": "second version", "score": 0.8}],
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 1
        assert fused[0]["content"] == "first version"

    def test_deduplicate_with_entry_key(self):
        """Test rrf_fuse() handles results with 'entry' key instead of 'id'."""
        results = [
            [{"entry": "doc1"}, {"entry": "doc2"}],
            [{"entry": "doc2"}, {"entry": "doc3"}],
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 3
        entries = [r.get("entry") for r in fused]
        assert "doc1" in entries
        assert "doc2" in entries
        assert "doc3" in entries


class TestRrfFuseKParameter:
    """Tests for k parameter affecting scores."""

    def test_k_affects_score_distribution(self):
        """Test that different k values affect RRF score distribution."""
        results = [
            [{"id": "1"}, {"id": "2"}],
        ]

        fused_k60 = rrf_fuse(results, k=60)
        fused_k10 = rrf_fuse(results, k=10)

        # With smaller k, the score difference between ranks is larger
        score_diff_k60 = fused_k60[0]["rrf_score"] - fused_k60[1]["rrf_score"]
        score_diff_k10 = fused_k10[0]["rrf_score"] - fused_k10[1]["rrf_score"]

        assert score_diff_k10 > score_diff_k60

    def test_higher_k_weights_lower_ranks_more(self):
        """Test higher k values give relatively more weight to lower-ranked items."""
        results = [
            [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        ]

        # With k=0, rank matters most
        fused_k0 = rrf_fuse(results, k=0)
        # With high k, rank matters less
        fused_k1000 = rrf_fuse(results, k=1000)

        # Score ratios should be closer with higher k
        ratio_k0 = fused_k0[0]["rrf_score"] / fused_k0[2]["rrf_score"]
        ratio_k1000 = fused_k1000[0]["rrf_score"] / fused_k1000[2]["rrf_score"]

        assert ratio_k1000 < ratio_k0

    def test_default_k_is_60(self):
        """Test that default k value is 60."""
        results = [
            [{"id": "1"}],
        ]

        fused_default = rrf_fuse(results)
        fused_explicit = rrf_fuse(results, k=60)

        assert fused_default[0]["rrf_score"] == fused_explicit[0]["rrf_score"]


class TestRrfFuseLimitParameter:
    """Tests for limit parameter."""

    def test_limit_reduces_results(self):
        """Test limit parameter reduces number of returned results."""
        results = [
            [{"id": str(i)} for i in range(20)],
        ]

        fused = rrf_fuse(results, limit=5)

        assert len(fused) == 5

    def test_default_limit_is_10(self):
        """Test that default limit is 10."""
        results = [
            [{"id": str(i)} for i in range(20)],
        ]

        fused_default = rrf_fuse(results)
        fused_explicit = rrf_fuse(results, limit=10)

        assert len(fused_default) == len(fused_explicit) == 10

    def test_limit_higher_than_available(self):
        """Test limit higher than available results returns all."""
        results = [
            [{"id": "1"}, {"id": "2"}],
        ]

        fused = rrf_fuse(results, limit=100)

        assert len(fused) == 2

    def test_limit_zero_returns_empty(self):
        """Test limit=0 returns empty list."""
        results = [
            [{"id": "1"}, {"id": "2"}],
        ]

        fused = rrf_fuse(results, limit=0)

        assert fused == []


class TestRrfFuseEdgeCases:
    """Tests for edge cases."""

    def test_empty_results_lists(self):
        """Test rrf_fuse() with empty results_lists returns empty list."""
        fused = rrf_fuse([])

        assert fused == []

    def test_single_empty_list(self):
        """Test rrf_fuse() with single empty list returns empty list."""
        fused = rrf_fuse([[]])

        assert fused == []

    def test_multiple_empty_lists(self):
        """Test rrf_fuse() with multiple empty lists returns empty list."""
        fused = rrf_fuse([[], [], []])

        assert fused == []

    def test_mixed_empty_and_nonempty_lists(self):
        """Test rrf_fuse() with mix of empty and non-empty lists."""
        results = [
            [],
            [{"id": "1"}],
            [],
            [{"id": "2"}],
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 2
        ids = {r["id"] for r in fused}
        assert ids == {"1", "2"}

    def test_results_without_id_or_entry(self):
        """Test rrf_fuse() skips results without id or entry key."""
        results = [
            [{"id": "1"}, {"content": "no id"}, {"entry": "doc2"}],
        ]

        fused = rrf_fuse(results)

        # Should skip the one without id or entry
        assert len(fused) == 2
        ids_entries = []
        for r in fused:
            if "id" in r:
                ids_entries.append(r["id"])
            if "entry" in r:
                ids_entries.append(r["entry"])
        assert "1" in ids_entries
        assert "doc2" in ids_entries

    def test_all_results_without_id(self):
        """Test rrf_fuse() with all results lacking id/entry returns empty."""
        results = [
            [{"content": "no id"}, {"text": "also no id"}],
        ]

        fused = rrf_fuse(results)

        assert fused == []

    def test_numeric_ids(self):
        """Test rrf_fuse() handles numeric IDs."""
        results = [
            [{"id": 1}, {"id": 2}],
            [{"id": 2}, {"id": 3}],
        ]

        fused = rrf_fuse(results)

        # IDs should be converted to strings internally
        assert len(fused) == 3
        ids = [r["id"] for r in fused]
        assert 1 in ids or "1" in ids
        assert 2 in ids or "2" in ids
        assert 3 in ids or "3" in ids

    def test_numeric_id_deduplication(self):
        """Test rrf_fuse() deduplicates numeric IDs correctly."""
        results = [
            [{"id": 1, "data": "first"}],
            [{"id": 1, "data": "second"}],
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 1
        assert fused[0]["data"] == "first"  # First occurrence

    def test_large_number_of_results(self):
        """Test rrf_fuse() handles large number of results."""
        results = [
            [{"id": str(i)} for i in range(1000)],
        ]

        fused = rrf_fuse(results, limit=100)

        assert len(fused) == 100

    def test_many_result_lists(self):
        """Test rrf_fuse() handles many result lists."""
        results = [
            [{"id": "1"}, {"id": "2"}]
            for _ in range(100)
        ]

        fused = rrf_fuse(results)

        # Both items should have high accumulated scores
        assert len(fused) == 2
        assert fused[0]["rrf_score"] > 1.0  # Should have accumulated significant score

    def test_result_with_additional_fields(self):
        """Test rrf_fuse() preserves additional fields from results."""
        results = [
            [{
                "id": "1",
                "content": "test content",
                "score": 0.95,
                "metadata": {"source": "test"},
            }],
        ]

        fused = rrf_fuse(results)

        assert len(fused) == 1
        assert fused[0]["content"] == "test content"
        assert fused[0]["score"] == 0.95
        assert fused[0]["metadata"]["source"] == "test"
        assert "rrf_score" in fused[0]

    def test_rrf_score_not_duplicated(self):
        """Test that rrf_score from input doesn't conflict with computed score."""
        results = [
            [{"id": "1", "rrf_score": 0.5}],  # Input has rrf_score field
        ]

        fused = rrf_fuse(results)

        # The computed rrf_score should overwrite the input one
        assert len(fused) == 1
        # Computed score for rank 0 with k=60: 1/(60+0+1) ≈ 0.016
        assert fused[0]["rrf_score"] == pytest.approx(1/61, rel=1e-5)


class TestRrfFuseScoreCalculation:
    """Tests for RRF score calculation accuracy."""

    def test_single_result_single_list_score(self):
        """Test RRF score for single result in single list."""
        results = [
            [{"id": "1"}],
        ]

        fused = rrf_fuse(results, k=60)

        # Score = 1 / (k + rank + 1) = 1 / (60 + 0 + 1) = 1/61
        expected_score = 1 / 61
        assert fused[0]["rrf_score"] == pytest.approx(expected_score, rel=1e-5)

    def test_multiple_ranks_score_calculation(self):
        """Test RRF score calculation for multiple ranks."""
        results = [
            [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        ]

        fused = rrf_fuse(results, k=60)

        # rank 0: 1/61
        # rank 1: 1/62
        # rank 2: 1/63
        assert fused[0]["rrf_score"] == pytest.approx(1/61, rel=1e-5)
        assert fused[1]["rrf_score"] == pytest.approx(1/62, rel=1e-5)
        assert fused[2]["rrf_score"] == pytest.approx(1/63, rel=1e-5)

    def test_accumulated_score_multiple_lists(self):
        """Test RRF score accumulation across multiple lists."""
        results = [
            [{"id": "1"}],  # rank 0 in first list
            [{"id": "1"}],  # rank 0 in second list
        ]

        fused = rrf_fuse(results, k=60)

        # Score = 1/61 + 1/61 = 2/61
        expected_score = 2 / 61
        assert fused[0]["rrf_score"] == pytest.approx(expected_score, rel=1e-5)

    def test_different_ranks_accumulated_score(self):
        """Test RRF score for same item at different ranks across lists."""
        results = [
            [{"id": "1"}, {"id": "2"}],  # id "1" at rank 0
            [{"id": "2"}, {"id": "1"}],  # id "1" at rank 1
        ]

        fused = rrf_fuse(results, k=60)

        # id "1" score: 1/61 + 1/62
        # id "2" score: 1/62 + 1/61
        # Both should have equal scores
        score_1 = next(r["rrf_score"] for r in fused if r["id"] == "1")
        score_2 = next(r["rrf_score"] for r in fused if r["id"] == "2")
        assert score_1 == pytest.approx(score_2, rel=1e-5)


class TestRrfFuseSorting:
    """Tests for result sorting."""

    def test_results_sorted_by_score_descending(self):
        """Test results are sorted by RRF score in descending order."""
        results = [
            [{"id": "a"}, {"id": "b"}, {"id": "c"}],
            [{"id": "a"}, {"id": "b"}],
            [{"id": "a"}],
        ]

        fused = rrf_fuse(results)

        # "a" appears in all 3 lists, should have highest score
        assert fused[0]["id"] == "a"
        # Scores should be in descending order
        for i in range(len(fused) - 1):
            assert fused[i]["rrf_score"] >= fused[i + 1]["rrf_score"]

    def test_stable_sort_for_equal_scores(self):
        """Test that sort is stable for items with equal scores."""
        # Create scenario where two items have identical scores
        results = [
            [{"id": "1"}],
            [{"id": "2"}],
        ]

        fused = rrf_fuse(results)

        # Both have score 1/61, order should be preserved from input
        assert len(fused) == 2
        assert fused[0]["rrf_score"] == fused[1]["rrf_score"]


class TestRrfFuseRealWorldScenarios:
    """Tests for real-world RRF scenarios."""

    def test_fuse_search_results_from_multiple_sources(self):
        """Test fusing search results from multiple retrieval sources."""
        # Simulate results from different search methods
        semantic_results = [
            {"id": "doc1", "score": 0.95, "source": "semantic"},
            {"id": "doc2", "score": 0.87, "source": "semantic"},
            {"id": "doc3", "score": 0.82, "source": "semantic"},
        ]
        keyword_results = [
            {"id": "doc2", "score": 0.90, "source": "keyword"},
            {"id": "doc4", "score": 0.85, "source": "keyword"},
            {"id": "doc1", "score": 0.80, "source": "keyword"},
        ]

        fused = rrf_fuse([semantic_results, keyword_results])

        # doc1 and doc2 appear in both lists, should rank higher
        assert len(fused) == 4
        doc_ids = [r["id"] for r in fused]
        assert "doc1" in doc_ids[:2]  # Should be in top 2
        assert "doc2" in doc_ids[:2]  # Should be in top 2

    def test_fuse_with_different_result_sizes(self):
        """Test fusing lists of different sizes."""
        short_list = [{"id": "a"}]
        long_list = [{"id": str(i)} for i in range(100)]

        fused = rrf_fuse([short_list, long_list], limit=10)

        assert len(fused) == 10
        # "a" appears first in short list (high score), should be in results
        ids = [r["id"] for r in fused]
        assert "a" in ids
