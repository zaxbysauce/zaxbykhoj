# Deprecation Timeline

This document tracks deprecated features and their removal schedule.

## max_tokens Parameter

### Status
- **Deprecated:** v2.0.0
- **Removal Date:** v2.2.0 (estimated Q2 2025)

### Description
The `max_tokens` parameter in `split_entries_by_max_tokens` method has been deprecated in favor of the more flexible `chunk_sizes` parameter.

### Migration Path

**Before (deprecated):**
```python
from khoj.processor.content.text_to_entries import TextToEntries

# Using max_tokens (deprecated)
entries = TextToEntries.split_entries_by_max_tokens(entries, max_tokens=256)
```

**After (recommended):**
```python
from khoj.processor.content.text_to_entries import TextToEntries

# Using chunk_sizes - single chunk size
entries = TextToEntries.split_entries_by_max_tokens(entries, chunk_sizes=[256])

# Using chunk_sizes - multiple scales (recommended for multi-scale chunking)
entries = TextToEntries.split_entries_by_max_tokens(entries, chunk_sizes=[512, 1024, 2048])
```

### Key Differences

| Feature | max_tokens | chunk_sizes |
|---------|------------|-------------|
| Single chunk size | ✅ | ✅ `[256]` |
| Multiple chunk sizes | ❌ | ✅ |
| Multi-scale retrieval | ❌ | ✅ |
| Future support | ❌ | ✅ |

### Migration Impact

- **Backward Compatible:** Yes. Code using `max_tokens` will continue to work until v2.2.0.
- **Deprecation Warning:** Users will see a `DeprecationWarning` when using `max_tokens`.
- **Action Required:** Update code to use `chunk_sizes` before v2.2.0.

### Affected Files

The following content processors use this parameter:
- `khoj/processor/content/org_mode/org_to_entries.py`
- `khoj/processor/content/markdown/markdown_to_entries.py`
- `khoj/processor/content/pdf/pdf_to_entries.py`
- `khoj/processor/content/images/image_to_entries.py`
- `khoj/processor/content/github/github_to_entries.py`
- `khoj/processor/content/plaintext/plaintext_to_entries.py`
- `khoj/processor/content/notion/notion_to_entries.py`
- `khoj/processor/content/docx/docx_to_entries.py`
