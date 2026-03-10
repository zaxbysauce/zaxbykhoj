"""Tests for Notion database processing in notion_to_entries.py"""
import pytest
from unittest.mock import MagicMock, patch

from khoj.processor.content.notion.notion_to_entries import NotionToEntries


# Test fixtures
@pytest.fixture
def mock_notion_config():
    """Create a mock NotionConfig for testing."""
    config = MagicMock()
    config.token = "test_token"
    return config


@pytest.fixture
def notion_processor(mock_notion_config):
    """Create a NotionToEntries instance with mocked config."""
    return NotionToEntries(mock_notion_config)


@pytest.fixture
def sample_database():
    """Sample Notion database object."""
    return {
        "object": "database",
        "id": "test-database-id-12345",
        "url": "https://notion.so/test-database",
    }


@pytest.fixture
def sample_db_metadata():
    """Sample database metadata from Notion API."""
    return {
        "id": "test-database-id-12345",
        "properties": {
            "Name": {
                "type": "title",
                "title": {}
            },
            "Status": {
                "type": "select",
                "select": {"name": "Status"}
            },
            "Tags": {
                "type": "multi_select",
                "multi_select": {"name": "Tags"}
            }
        }
    }


@pytest.fixture
def sample_database_row():
    """Sample row from Notion database query."""
    return {
        "id": "row-id-12345",
        "url": "https://notion.so/row-12345",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Test Entry"}]
            },
            "Status": {
                "type": "select",
                "select": {"name": "Active"}
            },
            "Tags": {
                "type": "multi_select",
                "multi_select": [{"name": "tag1"}, {"name": "tag2"}]
            }
        }
    }


class TestProcessDatabaseExists:
    """Test that process_database method exists and is callable."""

    def test_process_database_method_exists(self, notion_processor):
        """Verify process_database method exists on NotionToEntries class."""
        assert hasattr(notion_processor, 'process_database')
        assert callable(getattr(notion_processor, 'process_database'))

    def test_process_database_is_method(self, notion_processor):
        """Verify process_database is a bound method."""
        assert hasattr(notion_processor.process_database, '__call__')


class TestProcessDatabase:
    """Test process_database function handles databases correctly."""

    @patch.object(NotionToEntries, 'get_database')
    @patch('khoj.processor.content.notion.notion_to_entries.requests.Session')
    def test_process_database_returns_entries_for_valid_database(
        self, mock_session_class, mock_get_db, notion_processor, sample_database, sample_db_metadata, sample_database_row
    ):
        """Test that process_database returns entries when database has valid rows."""
        # Arrange
        mock_get_db.return_value = sample_db_metadata
        notion_processor.get_database = mock_get_db

        # Create a proper mock for the session
        mock_session_instance = MagicMock()
        notion_processor.session = mock_session_instance

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [sample_database_row],
            "has_more": False
        }

        notion_processor.session.post.return_value = mock_response

        # Mock get_page_children to return empty content (properties will be used)
        notion_processor.get_page_children = MagicMock(return_value={"results": []})

        # Act
        result = notion_processor.process_database(sample_database)

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0

    @patch.object(NotionToEntries, 'get_database')
    def test_process_database_handles_missing_metadata(self, mock_get_db, notion_processor, sample_database):
        """Test that process_database returns empty list when metadata cannot be retrieved."""
        # Arrange
        mock_get_db.return_value = None
        notion_processor.get_database = mock_get_db

        # Act
        result = notion_processor.process_database(sample_database)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0


class TestProcessDatabaseRow:
    """Test process_database_row function handles database rows correctly."""

    def test_process_database_row_with_content(self, notion_processor, sample_db_metadata, sample_database_row):
        """Test processing a database row that has content blocks."""
        # Arrange
        row_with_content = {
            "id": "row-id-12345",
            "url": "https://notion.so/row-12345",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Test Entry"}]
                }
            }
        }

        content_with_blocks = {
            "results": [
                {
                    "id": "block-12345",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"plain_text": "Some content", "type": "text"}]
                    },
                    "has_children": False
                }
            ]
        }

        notion_processor.get_page_children = MagicMock(return_value=content_with_blocks)

        # Act
        result = notion_processor.process_database_row(row_with_content, sample_db_metadata)

        # Assert
        assert isinstance(result, list)

    def test_process_database_row_without_content(self, notion_processor, sample_db_metadata, sample_database_row):
        """Test processing a database row with no content blocks falls back to properties."""
        # Arrange
        notion_processor.get_page_children = MagicMock(return_value={"results": []})

        # Act
        result = notion_processor.process_database_row(sample_database_row, sample_db_metadata)

        # Assert
        assert isinstance(result, list)
        # Should have at least one entry from properties
        assert len(result) >= 1


class TestExtractDatabaseTitle:
    """Test extract_database_title function."""

    def test_extract_title_from_database_row(self, notion_processor, sample_db_metadata, sample_database_row):
        """Test extracting title from a database row."""
        # Act
        result = notion_processor.extract_database_title(sample_database_row, sample_db_metadata)

        # Assert
        assert result == "Test Entry"

    def test_extract_title_returns_none_when_no_title_property(self, notion_processor):
        """Test extracting title returns None when row has no title property."""
        # Arrange
        db_metadata = {
            "properties": {
                "Status": {"type": "select"}
            }
        }
        row = {
            "properties": {
                "Status": {"type": "select", "select": {"name": "Active"}}
            }
        }

        # Act
        result = notion_processor.extract_database_title(row, db_metadata)

        # Assert
        assert result is None


class TestFormatDatabaseProperties:
    """Test format_database_properties function."""

    def test_format_properties_with_various_types(self, notion_processor, sample_database_row):
        """Test formatting database row properties."""
        # Act
        result = notion_processor.format_database_properties(sample_database_row, sample_db_metadata)

        # Assert
        assert result is not None
        assert "Name: Test Entry" in result
        assert "Status: Active" in result


class TestFormatPropertyValue:
    """Test format_property_value function for different property types."""

    def test_format_title_property(self, notion_processor):
        """Test formatting title property."""
        prop_data = {"type": "title", "title": [{"plain_text": "My Title"}]}
        result = notion_processor.format_property_value("title", prop_data)
        assert result == "My Title"

    def test_format_select_property(self, notion_processor):
        """Test formatting select property."""
        prop_data = {"type": "select", "select": {"name": "Done"}}
        result = notion_processor.format_property_value("select", prop_data)
        assert result == "Done"

    def test_format_multi_select_property(self, notion_processor):
        """Test formatting multi-select property."""
        prop_data = {"type": "multi_select", "multi_select": [{"name": "tag1"}, {"name": "tag2"}]}
        result = notion_processor.format_property_value("multi_select", prop_data)
        assert result == "tag1, tag2"

    def test_format_date_property(self, notion_processor):
        """Test formatting date property."""
        prop_data = {"type": "date", "date": {"start": "2024-01-15"}}
        result = notion_processor.format_property_value("date", prop_data)
        assert result == "2024-01-15"

    def test_format_checkbox_property_yes(self, notion_processor):
        """Test formatting checkbox property when True."""
        prop_data = {"type": "checkbox", "checkbox": True}
        result = notion_processor.format_property_value("checkbox", prop_data)
        assert result == "Yes"

    def test_format_checkbox_property_no(self, notion_processor):
        """Test formatting checkbox property when False."""
        prop_data = {"type": "checkbox", "checkbox": False}
        result = notion_processor.format_property_value("checkbox", prop_data)
        assert result == "No"

    def test_format_number_property(self, notion_processor):
        """Test formatting number property."""
        prop_data = {"type": "number", "number": 42}
        result = notion_processor.format_property_value("number", prop_data)
        assert result == "42"

    def test_format_url_property(self, notion_processor):
        """Test formatting URL property."""
        prop_data = {"type": "url", "url": "https://example.com"}
        result = notion_processor.format_property_value("url", prop_data)
        assert result == "https://example.com"


class TestProcessDatabasePagination:
    """Test process_database handles pagination correctly."""

    @patch.object(NotionToEntries, 'get_database')
    def test_process_database_handles_pagination(self, mock_get_db, notion_processor, sample_database, sample_db_metadata):
        """Test that process_database handles multiple pages of results."""
        # Arrange
        mock_get_db.return_value = sample_db_metadata
        notion_processor.get_database = mock_get_db

        # Create a proper mock for the session
        mock_session_instance = MagicMock()
        notion_processor.session = mock_session_instance

        # First page with more data, second page without
        first_page_response = {
            "results": [
                {
                    "id": "row-1",
                    "url": "https://notion.so/row-1",
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "Entry 1"}]}
                    }
                }
            ],
            "has_more": True,
            "next_cursor": "cursor-123"
        }

        second_page_response = {
            "results": [
                {
                    "id": "row-2",
                    "url": "https://notion.so/row-2",
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "Entry 2"}]}
                    }
                }
            ],
            "has_more": False
        }

        # Configure session.post to return different responses for different calls
        notion_processor.session.post.side_effect = [MagicMock(json=lambda: first_page_response), MagicMock(json=lambda: second_page_response)]

        # Mock get_page_children
        notion_processor.get_page_children = MagicMock(return_value={"results": []})

        # Act
        result = notion_processor.process_database(sample_database)

        # Assert
        assert isinstance(result, list)
        # Should have processed both pages
        assert notion_processor.session.post.call_count == 2


class TestProcessDatabaseEdgeCases:
    """Test process_database handles edge cases."""

    @patch.object(NotionToEntries, 'get_database')
    def test_process_database_with_empty_results(self, mock_get_db, notion_processor, sample_database, sample_db_metadata):
        """Test process_database handles empty database results."""
        # Arrange
        mock_get_db.return_value = sample_db_metadata
        notion_processor.get_database = mock_get_db

        # Create a proper mock for the session
        mock_session_instance = MagicMock()
        notion_processor.session = mock_session_instance

        notion_processor.session.post.return_value = MagicMock(json=lambda: {"results": [], "has_more": False})

        # Act
        result = notion_processor.process_database(sample_database)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0
