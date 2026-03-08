"""
Tests for rrf_fuse_multi function in khoj/utils/helpers.py

Tests cover:
- Basic multi-source fusion with overlapping results
- Empty sources handling
- Single source fusion
- Source weighting
- Limit parameter
- Source contribution tracking
- Results without IDs
- Deduplication of same results from multiple sources
"""

import pytest
from khoj.utils.helpers import rrf_fuse_multi


class TestRrfFuseMulti:
    """Test suite for rrf_fuse_multi function."""

    def test_rrf_fuse_multi_basic(self):
        """Test basic fusion with two sources having overlapping results."""
        # Source A: results 1, 2, 3
        source_a = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
            {"id": "doc3", "title": "Document 3"},
        ]
        # Source B: results 2, 3, 4 (overlap with A on doc2 and doc3)
        source_b = [
            {"id": "doc2", "title": "Document 2"},
            {"id": "doc3", "title": "Document 3"},
            {"id": "doc4", "title": "Document 4"},
        ]

        sources = {"source_a": source_a, "source_b": source_b}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Should return 4 unique documents
        assert len(result) == 4

        # doc2 and doc3 appear in both sources, so they should have higher scores
        # doc1 and doc4 appear only in one source each
        ids = [r["id"] for r in result]
        assert "doc2" in ids
        assert "doc3" in ids
        assert "doc1" in ids
        assert "doc4" in ids

        # Check that doc2 and doc3 have higher scores (they appear twice)
        scores = {r["id"]: r["rrf_score"] for r in result}
        assert scores["doc2"] > scores["doc1"]
        assert scores["doc2"] > scores["doc4"]
        assert scores["doc3"] > scores["doc1"]
        assert scores["doc3"] > scores["doc4"]

        # Verify RRF score calculation for doc1 (only in source_a, rank 0)
        # score = 1 * 1/(60 + 0 + 1) = 1/61
        expected_doc1_score = 1.0 / 61.0
        assert abs(scores["doc1"] - expected_doc1_score) < 1e-10

        # Verify RRF score calculation for doc2 (in both sources)
        # source_a rank 1: 1/(60 + 1 + 1) = 1/62
        # source_b rank 0: 1/(60 + 0 + 1) = 1/61
        # total = 1/62 + 1/61
        expected_doc2_score = 1.0/62.0 + 1.0/61.0
        assert abs(scores["doc2"] - expected_doc2_score) < 1e-10

    def test_rrf_fuse_multi_empty_sources(self):
        """Test that empty dict returns empty list."""
        result = rrf_fuse_multi({})
        assert result == []

    def test_rrf_fuse_multi_single_source(self):
        """Test that single source works correctly."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
            {"id": "doc3", "title": "Document 3"},
        ]

        sources = {"source_a": source_a}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Should return all 3 documents in order
        assert len(result) == 3
        assert result[0]["id"] == "doc1"
        assert result[1]["id"] == "doc2"
        assert result[2]["id"] == "doc3"

        # Verify scores are in descending order
        assert result[0]["rrf_score"] > result[1]["rrf_score"]
        assert result[1]["rrf_score"] > result[2]["rrf_score"]

        # Verify exact RRF scores
        # rank 0: 1/(60 + 0 + 1) = 1/61
        # rank 1: 1/(60 + 1 + 1) = 1/62
        # rank 2: 1/(60 + 2 + 1) = 1/63
        assert abs(result[0]["rrf_score"] - 1.0/61.0) < 1e-10
        assert abs(result[1]["rrf_score"] - 1.0/62.0) < 1e-10
        assert abs(result[2]["rrf_score"] - 1.0/63.0) < 1e-10

    def test_rrf_fuse_multi_source_weights(self):
        """Test that weighted fusion produces correct scores."""
        # Same results in both sources
        source_a = [
            {"id": "doc1", "title": "Document 1"},
        ]
        source_b = [
            {"id": "doc1", "title": "Document 1"},
        ]

        sources = {"source_a": source_a, "source_b": source_b}
        source_weights = {"source_a": 2.0, "source_b": 1.0}

        result = rrf_fuse_multi(sources, k=60, limit=10, source_weights=source_weights)

        assert len(result) == 1
        assert result[0]["id"] == "doc1"

        # Verify weighted RRF score
        # source_a contribution: 2.0 * 1/(60 + 0 + 1) = 2/61
        # source_b contribution: 1.0 * 1/(60 + 0 + 1) = 1/61
        # total = 3/61
        expected_score = 3.0 / 61.0
        assert abs(result[0]["rrf_score"] - expected_score) < 1e-10

    def test_rrf_fuse_multi_limit(self):
        """Test that limit parameter is respected."""
        source_a = [
            {"id": f"doc{i}", "title": f"Document {i}"}
            for i in range(20)
        ]

        sources = {"source_a": source_a}

        # Test with limit=5
        result = rrf_fuse_multi(sources, k=60, limit=5)
        assert len(result) == 5

        # Test with limit=10
        result = rrf_fuse_multi(sources, k=60, limit=10)
        assert len(result) == 10

        # Test with limit larger than results
        result = rrf_fuse_multi(sources, k=60, limit=100)
        assert len(result) == 20

    def test_rrf_fuse_multi_source_contributions(self):
        """Test that source contributions are tracked correctly."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
        ]
        source_b = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc3", "title": "Document 3"},
        ]

        sources = {"source_a": source_a, "source_b": source_b}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Find doc1 in results
        doc1_result = next(r for r in result if r["id"] == "doc1")

        # doc1 should have contributions from both sources
        assert "source_contributions" in doc1_result
        assert "source_a" in doc1_result["source_contributions"]
        assert "source_b" in doc1_result["source_contributions"]

        # Verify contribution values
        # source_a rank 0: 1/(60 + 0 + 1) = 1/61
        # source_b rank 0: 1/(60 + 0 + 1) = 1/61
        expected_contribution = 1.0 / 61.0
        assert abs(doc1_result["source_contributions"]["source_a"] - expected_contribution) < 1e-10
        assert abs(doc1_result["source_contributions"]["source_b"] - expected_contribution) < 1e-10

        # Find doc2 in results - should only have contribution from source_a
        doc2_result = next(r for r in result if r["id"] == "doc2")
        assert "source_a" in doc2_result["source_contributions"]
        assert "source_b" not in doc2_result["source_contributions"]

    def test_rrf_fuse_multi_no_ids(self):
        """Test that results without id or entry keys are skipped."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
            {"title": "No ID Document"},  # No id or entry key
            {"entry": "doc2", "title": "Document 2"},
            {"content": "Another no ID"},  # No id or entry key
        ]

        sources = {"source_a": source_a}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Should only have 2 results (doc1 and doc2)
        assert len(result) == 2
        ids = [r.get("id") or r.get("entry") for r in result]
        assert "doc1" in ids
        assert "doc2" in ids

    def test_rrf_fuse_multi_deduplication(self):
        """Test that same result from multiple sources is deduplicated."""
        # Same document appears in multiple sources with same ID
        source_a = [
            {"id": "doc1", "title": "Document 1 from A"},
            {"id": "doc2", "title": "Document 2 from A"},
        ]
        source_b = [
            {"id": "doc1", "title": "Document 1 from B"},  # Same ID as in A
            {"id": "doc3", "title": "Document 3 from B"},
        ]
        source_c = [
            {"id": "doc1", "title": "Document 1 from C"},  # Same ID again
        ]

        sources = {"source_a": source_a, "source_b": source_b, "source_c": source_c}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Should have 3 unique documents
        assert len(result) == 3

        # doc1 should appear only once but with combined score
        doc1_results = [r for r in result if r["id"] == "doc1"]
        assert len(doc1_results) == 1

        # Verify doc1 has the highest score (appears in all 3 sources)
        scores = {r["id"]: r["rrf_score"] for r in result}
        assert scores["doc1"] > scores["doc2"]
        assert scores["doc1"] > scores["doc3"]

        # Verify the exact score: 3 * 1/61 = 3/61
        expected_doc1_score = 3.0 / 61.0
        assert abs(scores["doc1"] - expected_doc1_score) < 1e-10

        # Verify source contributions for doc1
        doc1 = doc1_results[0]
        assert len(doc1["source_contributions"]) == 3
        assert "source_a" in doc1["source_contributions"]
        assert "source_b" in doc1["source_contributions"]
        assert "source_c" in doc1["source_contributions"]

    def test_rrf_fuse_multi_empty_source_list(self):
        """Test that empty source lists are handled gracefully."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
        ]
        source_b = []  # Empty list

        sources = {"source_a": source_a, "source_b": source_b}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Should still return results from source_a
        assert len(result) == 1
        assert result[0]["id"] == "doc1"

    def test_rrf_fuse_multi_all_empty_sources(self):
        """Test that all empty source lists return empty result."""
        sources = {"source_a": [], "source_b": []}
        result = rrf_fuse_multi(sources, k=60, limit=10)
        assert result == []

    def test_rrf_fuse_multi_entry_key(self):
        """Test that 'entry' key is used as alternative to 'id'."""
        source_a = [
            {"entry": "entry1", "title": "Entry 1"},
            {"entry": "entry2", "title": "Entry 2"},
        ]

        sources = {"source_a": source_a}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        assert len(result) == 2
        # Results should use entry as the identifier
        assert result[0].get("entry") == "entry1"
        assert result[1].get("entry") == "entry2"

    def test_rrf_fuse_multi_mixed_id_entry(self):
        """Test mixing results with 'id' and 'entry' keys."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
        ]
        source_b = [
            {"entry": "doc1", "title": "Same as doc1 but with entry key"},
        ]

        sources = {"source_a": source_a, "source_b": source_b}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        # Both should be treated as the same ID since they're converted to strings
        assert len(result) == 1
        assert result[0]["rrf_score"] == 2.0 / 61.0  # From both sources

    def test_rrf_fuse_multi_default_k_and_limit(self):
        """Test that default k=60 and limit=10 work correctly."""
        source_a = [
            {"id": f"doc{i}", "title": f"Document {i}"}
            for i in range(15)
        ]

        sources = {"source_a": source_a}
        result = rrf_fuse_multi(sources)  # Use defaults

        # Default limit is 10
        assert len(result) == 10

        # Verify first score uses default k=60
        # rank 0: 1/(60 + 0 + 1) = 1/61
        assert abs(result[0]["rrf_score"] - 1.0/61.0) < 1e-10

    def test_rrf_fuse_multi_different_k_values(self):
        """Test that different k values affect scores correctly."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
        ]

        sources = {"source_a": source_a}

        # With k=60
        result_k60 = rrf_fuse_multi(sources, k=60, limit=10)
        score_k60_doc2 = result_k60[1]["rrf_score"]  # rank 1

        # With k=0
        result_k0 = rrf_fuse_multi(sources, k=0, limit=10)
        score_k0_doc2 = result_k0[1]["rrf_score"]  # rank 1

        # Higher k should give relatively more weight to lower-ranked items
        # k=60, rank=1: 1/(60+1+1) = 1/62
        # k=0, rank=1: 1/(0+1+1) = 1/2
        assert abs(score_k60_doc2 - 1.0/62.0) < 1e-10
        assert abs(score_k0_doc2 - 1.0/2.0) < 1e-10
        assert score_k0_doc2 > score_k60_doc2

    def test_rrf_fuse_multi_preserves_original_data(self):
        """Test that original result data is preserved in output."""
        source_a = [
            {"id": "doc1", "title": "Document 1", "score": 0.95, "metadata": {"author": "Alice"}},
        ]

        sources = {"source_a": source_a}
        result = rrf_fuse_multi(sources, k=60, limit=10)

        assert len(result) == 1
        assert result[0]["id"] == "doc1"
        assert result[0]["title"] == "Document 1"
        assert result[0]["score"] == 0.95
        assert result[0]["metadata"] == {"author": "Alice"}
        # Should also have RRF-specific fields
        assert "rrf_score" in result[0]
        assert "source_contributions" in result[0]

    def test_rrf_fuse_multi_partial_weights(self):
        """Test that unspecified sources get default weight of 1.0."""
        source_a = [
            {"id": "doc1", "title": "Document 1"},
        ]
        source_b = [
            {"id": "doc1", "title": "Document 1"},
        ]
        source_c = [
            {"id": "doc1", "title": "Document 1"},
        ]

        sources = {"source_a": source_a, "source_b": source_b, "source_c": source_c}
        # Only specify weight for source_a
        source_weights = {"source_a": 2.0}

        result = rrf_fuse_multi(sources, k=60, limit=10, source_weights=source_weights)

        # Score should be: 2.0/61 + 1.0/61 + 1.0/61 = 4.0/61
        expected_score = 4.0 / 61.0
        assert abs(result[0]["rrf_score"] - expected_score) < 1e-10

        # Verify source contributions
        contributions = result[0]["source_contributions"]
        assert abs(contributions["source_a"] - 2.0/61.0) < 1e-10
        assert abs(contributions["source_b"] - 1.0/61.0) < 1e-10
        assert abs(contributions["source_c"] - 1.0/61.0) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
