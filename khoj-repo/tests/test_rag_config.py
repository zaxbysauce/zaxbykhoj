"""Tests for RagConfig class in khoj/utils/config.py"""

import pytest
from khoj.utils.config import RagConfig


class TestRagConfig:
    """Test suite for RagConfig class"""

    def test_rag_config_defaults(self):
        """Verify all default values are correctly set"""
        config = RagConfig()
        
        # Feature flags
        assert config.crag_enabled is True
        assert config.query_transform_enabled is True
        assert config.hybrid_search_enabled is True
        assert config.contextual_chunking_enabled is False
        assert config.multi_scale_chunking_enabled is False
        assert config.tri_vector_search_enabled is False
        
        # Additional settings
        assert config.multi_scale_chunk_sizes == [512, 1024, 2048]
        assert config.hybrid_alpha == 0.6

    def test_rag_config_types(self):
        """Verify type hints are correct by checking attribute types"""
        config = RagConfig()
        
        # Boolean types
        assert isinstance(config.crag_enabled, bool)
        assert isinstance(config.query_transform_enabled, bool)
        assert isinstance(config.hybrid_search_enabled, bool)
        assert isinstance(config.contextual_chunking_enabled, bool)
        assert isinstance(config.multi_scale_chunking_enabled, bool)
        assert isinstance(config.tri_vector_search_enabled, bool)
        
        # List type
        assert isinstance(config.multi_scale_chunk_sizes, list)
        assert all(isinstance(size, int) for size in config.multi_scale_chunk_sizes)
        
        # Float type
        assert isinstance(config.hybrid_alpha, float)

    def test_crag_enabled_default(self):
        """Verify crag_enabled defaults to True"""
        config = RagConfig()
        assert config.crag_enabled is True

    def test_query_transform_enabled_default(self):
        """Verify query_transform_enabled defaults to True"""
        config = RagConfig()
        assert config.query_transform_enabled is True

    def test_hybrid_search_enabled_default(self):
        """Verify hybrid_search_enabled defaults to True"""
        config = RagConfig()
        assert config.hybrid_search_enabled is True

    def test_contextual_chunking_enabled_default(self):
        """Verify contextual_chunking_enabled defaults to False"""
        config = RagConfig()
        assert config.contextual_chunking_enabled is False

    def test_multi_scale_chunking_enabled_default(self):
        """Verify multi_scale_chunking_enabled defaults to False"""
        config = RagConfig()
        assert config.multi_scale_chunking_enabled is False

    def test_tri_vector_search_enabled_default(self):
        """Verify tri_vector_search_enabled defaults to False"""
        config = RagConfig()
        assert config.tri_vector_search_enabled is False

    def test_multi_scale_chunk_sizes_default(self):
        """Verify multi_scale_chunk_sizes defaults to [512, 1024, 2048]"""
        config = RagConfig()
        assert config.multi_scale_chunk_sizes == [512, 1024, 2048]

    def test_hybrid_alpha_default(self):
        """Verify hybrid_alpha defaults to 0.6"""
        config = RagConfig()
        assert config.hybrid_alpha == 0.6


class TestRagConfigMutability:
    """Test that config values can be modified"""

    def test_can_modify_crag_enabled(self):
        """Verify crag_enabled can be modified"""
        config = RagConfig()
        config.crag_enabled = False
        assert config.crag_enabled is False

    def test_can_modify_query_transform_enabled(self):
        """Verify query_transform_enabled can be modified"""
        config = RagConfig()
        config.query_transform_enabled = False
        assert config.query_transform_enabled is False

    def test_can_modify_hybrid_search_enabled(self):
        """Verify hybrid_search_enabled can be modified"""
        config = RagConfig()
        config.hybrid_search_enabled = False
        assert config.hybrid_search_enabled is False

    def test_can_modify_contextual_chunking_enabled(self):
        """Verify contextual_chunking_enabled can be modified"""
        config = RagConfig()
        config.contextual_chunking_enabled = True
        assert config.contextual_chunking_enabled is True

    def test_can_modify_multi_scale_chunking_enabled(self):
        """Verify multi_scale_chunking_enabled can be modified"""
        config = RagConfig()
        config.multi_scale_chunking_enabled = True
        assert config.multi_scale_chunking_enabled is True

    def test_can_modify_tri_vector_search_enabled(self):
        """Verify tri_vector_search_enabled can be modified"""
        config = RagConfig()
        config.tri_vector_search_enabled = True
        assert config.tri_vector_search_enabled is True

    def test_can_modify_multi_scale_chunk_sizes(self):
        """Verify multi_scale_chunk_sizes can be modified"""
        config = RagConfig()
        config.multi_scale_chunk_sizes = [256, 512]
        assert config.multi_scale_chunk_sizes == [256, 512]

    def test_can_modify_hybrid_alpha(self):
        """Verify hybrid_alpha can be modified"""
        config = RagConfig()
        config.hybrid_alpha = 0.8
        assert config.hybrid_alpha == 0.8


class TestRagConfigEdgeCases:
    """Test edge cases for RagConfig"""

    def test_hybrid_alpha_boundary_values(self):
        """Verify hybrid_alpha accepts boundary values"""
        config = RagConfig()
        
        # Test 0.0
        config.hybrid_alpha = 0.0
        assert config.hybrid_alpha == 0.0
        
        # Test 1.0
        config.hybrid_alpha = 1.0
        assert config.hybrid_alpha == 1.0

    def test_multi_scale_chunk_sizes_empty_list(self):
        """Verify multi_scale_chunk_sizes can be empty list"""
        config = RagConfig()
        config.multi_scale_chunk_sizes = []
        assert config.multi_scale_chunk_sizes == []

    def test_multi_scale_chunk_sizes_single_element(self):
        """Verify multi_scale_chunk_sizes can have single element"""
        config = RagConfig()
        config.multi_scale_chunk_sizes = [1024]
        assert config.multi_scale_chunk_sizes == [1024]

    def test_multiple_instances_independent(self):
        """Verify multiple instances have independent values"""
        config1 = RagConfig()
        config2 = RagConfig()
        
        # Modify config1
        config1.crag_enabled = False
        config1.hybrid_alpha = 0.9
        
        # config2 should still have defaults
        assert config2.crag_enabled is True
        assert config2.hybrid_alpha == 0.6
