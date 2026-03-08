#!/usr/bin/env python
"""
Standalone test runner for multi-scale chunking tests.
This runs tests without requiring a database connection.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up Django settings BEFORE any imports
os.environ['DJANGO_SETTINGS_MODULE'] = 'khoj.app.settings'

import django
from django.conf import settings

# Configure settings to use SQLite instead of PostgreSQL for testing
settings.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for testing
settings.MIGRATION_MODULES = {
    app: None for app in settings.INSTALLED_APPS if isinstance(app, str)
}

django.setup()

# Now import the modules we want to test
from khoj.processor.content.text_to_entries import TextToEntries
from khoj.utils.rawconfig import Entry
import uuid
import unittest


class TestEntryChunkScaleField(unittest.TestCase):
    """Test cases for Entry class chunk_scale field."""

    def test_entry_chunk_scale_field(self):
        """Verify Entry class accepts and stores chunk_scale."""
        entry = Entry(
            raw="Test raw content",
            compiled="Test compiled content",
            heading="Test Heading",
            file="test.txt",
            corpus_id=uuid.uuid4(),
            chunk_scale="512",
        )
        self.assertEqual(entry.chunk_scale, "512")
        self.assertTrue(hasattr(entry, "chunk_scale"))

    def test_entry_chunk_scale_optional(self):
        """Verify Entry class works without chunk_scale (backward compatibility)."""
        entry = Entry(
            raw="Test raw content",
            compiled="Test compiled content",
            heading="Test Heading",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )
        self.assertIsNone(entry.chunk_scale)

    def test_entry_chunk_scale_default(self):
        """Verify Entry class accepts 'default' as chunk_scale."""
        entry = Entry(
            raw="Test raw content",
            compiled="Test compiled content",
            heading="Test Heading",
            file="test.txt",
            corpus_id=uuid.uuid4(),
            chunk_scale="default",
        )
        self.assertEqual(entry.chunk_scale, "default")


class TestSplitEntriesBackwardCompat(unittest.TestCase):
    """Test cases for backward compatibility with max_tokens parameter."""

    def test_split_entries_single_scale_backward_compat(self):
        """max_tokens=256 should use 'default' scale."""
        raw_content = " ".join([f"word{i}" for i in range(300)])
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            max_tokens=256,
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertEqual(chunk.chunk_scale, "default")

    def test_split_entries_max_tokens_creates_single_chunk_when_small(self):
        """Small content with max_tokens should create single chunk."""
        raw_content = "Small content"
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            max_tokens=256,
            raw_is_compiled=True,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].chunk_scale, "default")


class TestSplitEntriesMultiScale(unittest.TestCase):
    """Test cases for multi-scale chunking with chunk_sizes parameter."""

    def test_split_entries_multi_scale(self):
        """chunk_sizes=[512, 1024] creates chunks at both scales."""
        paragraphs = []
        for i in range(50):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512, 1024],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        scales = set(chunk.chunk_scale for chunk in result)
        self.assertIn("512", scales)
        self.assertIn("1024", scales)

    def test_split_entries_three_scales(self):
        """chunk_sizes=[256, 512, 1024] creates chunks at all three scales."""
        paragraphs = []
        for i in range(100):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(15)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[256, 512, 1024],
            raw_is_compiled=True,
        )

        scales = set(chunk.chunk_scale for chunk in result)
        self.assertIn("256", scales)
        self.assertIn("512", scales)
        self.assertIn("1024", scales)


class TestSplitEntriesDefaultSizes(unittest.TestCase):
    """Test cases for default chunk sizes behavior."""

    def test_split_entries_default_sizes(self):
        """No args uses [512, 1024, 2048]."""
        paragraphs = []
        for i in range(150):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        scales = set(chunk.chunk_scale for chunk in result)
        self.assertIn("512", scales)
        self.assertIn("1024", scales)
        self.assertIn("2048", scales)


class TestChunkScaleTagging(unittest.TestCase):
    """Test cases for chunk scale tagging behavior."""

    def test_chunk_scale_single_scale_default(self):
        """Single scale uses 'default' tag."""
        raw_content = "Some test content that is long enough to be processed"
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertEqual(chunk.chunk_scale, "default")

    def test_chunk_scale_multiple_scales_labeled(self):
        """Multiple scales use size as string label."""
        paragraphs = []
        for i in range(50):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512, 1024],
            raw_is_compiled=True,
        )

        scales = set(chunk.chunk_scale for chunk in result)
        self.assertNotIn("default", scales)
        self.assertIn("512", scales)
        self.assertIn("1024", scales)


class TestSharedCorpusId(unittest.TestCase):
    """Test cases for shared corpus_id across chunks from same entry."""

    def test_shared_corpus_id_single_scale(self):
        """All chunks from same entry share corpus_id with single scale."""
        paragraphs = []
        for i in range(50):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[256],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 1)
        corpus_ids = set(chunk.corpus_id for chunk in result)
        self.assertEqual(len(corpus_ids), 1)

    def test_shared_corpus_id_multi_scale(self):
        """All chunks from same entry share corpus_id across all scales."""
        paragraphs = []
        for i in range(100):
            paragraphs.append(f"Paragraph {i}: " + " ".join([f"word{j}" for j in range(20)]))
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512, 1024],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 2)
        corpus_ids = set(chunk.corpus_id for chunk in result)
        self.assertEqual(len(corpus_ids), 1)

    def test_different_entries_different_corpus_ids(self):
        """Chunks from different entries have different corpus_ids."""
        entry1 = Entry(
            raw="Content for entry 1 " * 50,
            compiled="Content for entry 1 " * 50,
            heading="Entry 1",
            file="test1.txt",
            corpus_id=uuid.uuid4(),
        )
        entry2 = Entry(
            raw="Content for entry 2 " * 50,
            compiled="Content for entry 2 " * 50,
            heading="Entry 2",
            file="test2.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry1, entry2],
            chunk_sizes=[256],
            raw_is_compiled=True,
        )

        entry1_chunks = [c for c in result if c.file == "test1.txt"]
        entry2_chunks = [c for c in result if c.file == "test2.txt"]

        self.assertGreater(len(entry1_chunks), 0)
        self.assertGreater(len(entry2_chunks), 0)

        entry1_corpus_ids = set(c.corpus_id for c in entry1_chunks)
        entry2_corpus_ids = set(c.corpus_id for c in entry2_chunks)

        self.assertEqual(len(entry1_corpus_ids), 1)
        self.assertEqual(len(entry2_corpus_ids), 1)
        self.assertNotEqual(entry1_corpus_ids, entry2_corpus_ids)


class TestEmptyEntriesHandling(unittest.TestCase):
    """Test cases for empty entries handling."""

    def test_empty_entries_handled(self):
        """Empty entries are skipped gracefully."""
        empty_entry = Entry(
            raw="",
            compiled="",
            heading="Empty",
            file="empty.txt",
            corpus_id=uuid.uuid4(),
        )
        valid_entry = Entry(
            raw="Valid content here",
            compiled="Valid content here",
            heading="Valid",
            file="valid.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [empty_entry, valid_entry],
            chunk_sizes=[512],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertEqual(chunk.file, "valid.txt")

    def test_all_empty_entries_returns_empty(self):
        """All empty entries returns empty list."""
        empty_entry1 = Entry(
            raw="",
            compiled="",
            heading="Empty1",
            file="empty1.txt",
            corpus_id=uuid.uuid4(),
        )
        empty_entry2 = Entry(
            raw="",
            compiled="",
            heading="Empty2",
            file="empty2.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [empty_entry1, empty_entry2],
            chunk_sizes=[512],
            raw_is_compiled=True,
        )

        self.assertEqual(len(result), 0)

    def test_none_compiled_handled(self):
        """Entries with None compiled are skipped."""
        none_entry = Entry(
            raw=None,
            compiled=None,
            heading="None",
            file="none.txt",
            corpus_id=uuid.uuid4(),
        )
        valid_entry = Entry(
            raw="Valid content",
            compiled="Valid content",
            heading="Valid",
            file="valid.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [none_entry, valid_entry],
            chunk_sizes=[512],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertEqual(chunk.file, "valid.txt")


class TestFromDictWithChunkScale(unittest.TestCase):
    """Test cases for Entry.from_dict with chunk_scale."""

    def test_from_dict_with_chunk_scale(self):
        """Entry.from_dict handles chunk_scale."""
        data = {
            "raw": "Test raw content",
            "compiled": "Test compiled content",
            "heading": "Test Heading",
            "file": "test.txt",
            "corpus_id": str(uuid.uuid4()),
            "uri": "file://test.txt",
            "chunk_scale": "512",
        }

        entry = Entry.from_dict(data)

        self.assertEqual(entry.chunk_scale, "512")
        self.assertEqual(entry.raw, "Test raw content")
        self.assertEqual(entry.compiled, "Test compiled content")
        self.assertEqual(entry.heading, "Test Heading")
        self.assertEqual(entry.file, "test.txt")

    def test_from_dict_without_chunk_scale(self):
        """Entry.from_dict works without chunk_scale (backward compatibility)."""
        data = {
            "raw": "Test raw content",
            "compiled": "Test compiled content",
            "heading": "Test Heading",
            "file": "test.txt",
            "corpus_id": str(uuid.uuid4()),
        }

        entry = Entry.from_dict(data)

        self.assertIsNone(entry.chunk_scale)
        self.assertEqual(entry.raw, "Test raw content")

    def test_from_dict_with_default_chunk_scale(self):
        """Entry.from_dict handles 'default' chunk_scale."""
        data = {
            "raw": "Test raw content",
            "compiled": "Test compiled content",
            "heading": "Test Heading",
            "file": "test.txt",
            "corpus_id": str(uuid.uuid4()),
            "chunk_scale": "default",
        }

        entry = Entry.from_dict(data)

        self.assertEqual(entry.chunk_scale, "default")


class TestEntryJsonSerialization(unittest.TestCase):
    """Test cases for Entry JSON serialization with chunk_scale."""

    def test_to_json_includes_chunk_scale(self):
        """Entry.to_json includes chunk_scale field."""
        entry = Entry(
            raw="Test raw",
            compiled="Test compiled",
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
            chunk_scale="512",
        )

        json_str = entry.to_json()

        self.assertIn("chunk_scale", json_str)
        self.assertIn("512", json_str)

    def test_to_json_without_chunk_scale(self):
        """Entry.to_json works when chunk_scale is None."""
        entry = Entry(
            raw="Test raw",
            compiled="Test compiled",
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        json_str = entry.to_json()

        self.assertIn("chunk_scale", json_str)


class TestChunkContentIntegrity(unittest.TestCase):
    """Test cases for chunk content integrity."""

    def test_chunk_content_preserved(self):
        """Original content is preserved in chunks."""
        raw_content = "This is the first sentence. This is the second sentence. This is the third sentence."
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[10],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        combined = " ".join(chunk.compiled for chunk in result)
        self.assertIn("first sentence", combined)
        self.assertIn("second sentence", combined)
        self.assertIn("third sentence", combined)

    def test_chunk_heading_prepended_to_subsequent_chunks(self):
        """Heading is prepended to chunks after the first."""
        paragraphs = []
        for i in range(20):
            paragraphs.append(f"Paragraph {i}: " + "word " * 50)
        raw_content = "\n\n".join(paragraphs)

        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="TestHeading",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[50],
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 1)
        for i, chunk in enumerate(result[1:], 1):
            self.assertIn("TestHeading", chunk.compiled, f"Chunk {i} should have heading prepended")


class TestLongWordsRemoval(unittest.TestCase):
    """Test cases for long words removal in chunks."""

    def test_long_words_removed(self):
        """Words longer than max_word_length are removed."""
        long_word = "a" * 1000
        raw_content = f"Normal words here {long_word} more normal words"
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512],
            max_word_length=100,
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertNotIn(long_word, chunk.compiled)

    def test_normal_words_preserved(self):
        """Normal length words are preserved."""
        raw_content = "These are all normal length words that should be preserved."
        entry = Entry(
            raw=raw_content,
            compiled=raw_content,
            heading="Test",
            file="test.txt",
            corpus_id=uuid.uuid4(),
        )

        result = TextToEntries.split_entries_by_max_tokens(
            [entry],
            chunk_sizes=[512],
            max_word_length=500,
            raw_is_compiled=True,
        )

        self.assertGreater(len(result), 0)
        for chunk in result:
            self.assertIn("normal length words", chunk.compiled)


class TestCleanField(unittest.TestCase):
    """Test cases for clean_field static method."""

    def test_null_characters_removed(self):
        """Null characters are removed from fields."""
        text_with_null = "Hello\x00World\x00Test"

        cleaned = TextToEntries.clean_field(text_with_null)

        self.assertNotIn("\x00", cleaned)
        self.assertEqual(cleaned, "HelloWorldTest")

    def test_empty_string_handled(self):
        """Empty string is handled gracefully."""
        cleaned = TextToEntries.clean_field("")

        self.assertEqual(cleaned, "")

    def test_none_handled(self):
        """None is handled gracefully."""
        cleaned = TextToEntries.clean_field(None)

        self.assertTrue(cleaned is None or cleaned == "")


class TestTokenizer(unittest.TestCase):
    """Test cases for tokenizer static method."""

    def test_tokenizer_splits_on_whitespace(self):
        """Tokenizer splits text on whitespace."""
        text = "one two three four"

        tokens = TextToEntries.tokenizer(text)

        self.assertEqual(tokens, ["one", "two", "three", "four"])

    def test_tokenizer_empty_string(self):
        """Tokenizer handles empty string."""
        tokens = TextToEntries.tokenizer("")

        self.assertEqual(tokens, [])

    def test_tokenizer_multiple_spaces(self):
        """Tokenizer handles multiple spaces."""
        text = "one  two   three"

        tokens = TextToEntries.tokenizer(text)

        # Tokenizer splits on whitespace, multiple spaces may be collapsed
        self.assertIn("one", tokens)
        self.assertIn("two", tokens)
        self.assertIn("three", tokens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
