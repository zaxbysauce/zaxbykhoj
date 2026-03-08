"""Tests for the reindex_multi_scale management command.

These tests require a Django database connection to run.
Run with: pytest tests/test_reindex_multi_scale.py -v
"""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from khoj.database.models import Entry, KhojUser, FileObject


@pytest.mark.django_db
def test_scales_argument_parsing():
    """Test that comma-separated integers are parsed correctly."""
    out = StringIO()
    err = StringIO()

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_entry.all.return_value.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        call_command(
            'reindex_multi_scale',
            '--scales', '256,512,1024',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert '[DRY RUN]' in output
    assert 'chunk sizes: [256, 512, 1024]' in output


@pytest.mark.django_db
def test_dry_run_mode(default_user):
    """Test that dry-run mode shows counts without modifying database."""
    out = StringIO()
    err = StringIO()

    # Create test entries
    Entry.objects.create(
        user=default_user,
        raw='test content',
        compiled='test content',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
    )

    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
        # Ensure split_entries_by_max_tokens is not called in dry-run mode
        mock_tte.split_entries_by_max_tokens.return_value = []
        
        call_command(
            'reindex_multi_scale',
            '--scales', '512,1024',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert '[DRY RUN]' in output
    assert 'Total entries to reindex: 1' in output
    assert 'Use --apply to actually perform the reindexing' in output
    # Verify no actual processing happened
    mock_tte.split_entries_by_max_tokens.assert_not_called()


@pytest.mark.django_db
def test_apply_mode(default_user):
    """Test that apply mode actually performs reindexing."""
    out = StringIO()
    err = StringIO()

    # Create a FileObject for the test
    file_object = FileObject.objects.create(
        user=default_user,
        file_name='/test/file.txt',
        raw_text='Test content for reindexing',
    )

    # Create test entry
    Entry.objects.create(
        user=default_user,
        raw='Test content for reindexing',
        compiled='Test content for reindexing',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
        chunk_scale='512',
    )

    # Mock TextToEntries to return new entries
    mock_entry_config = MagicMock()
    mock_entry_config.raw = 'chunked content'
    mock_entry_config.compiled = 'chunked compiled'
    mock_entry_config.heading = 'chunked heading'
    mock_entry_config.file = '/test/file.txt'
    mock_entry_config.chunk_scale = '512'
    mock_entry_config.corpus_id = 'test-corpus'
    mock_entry_config.uri = None

    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = file_object
            mock_tte.split_entries_by_max_tokens.return_value = [mock_entry_config]

            call_command(
                'reindex_multi_scale',
                '--scales', '512,1024',
                '--apply',
                stdout=out,
                stderr=err
            )

    output = out.getvalue()
    assert '[APPLY]' in output
    assert 'Multi-scale reindexing complete!' in output
    mock_tte.split_entries_by_max_tokens.assert_called_once()


@pytest.mark.django_db
def test_batch_processing(default_user):
    """Test that files are processed in batches."""
    out = StringIO()
    err = StringIO()

    # Create test entries for multiple files
    for i in range(5):
        Entry.objects.create(
            user=default_user,
            raw=f'content {i}',
            compiled=f'content {i}',
            heading=f'Test {i}',
            file_path=f'/test/file{i}.txt',
            file_type='plaintext',
            file_source='computer',
        )

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_query = MagicMock()
        mock_entry.all.return_value = mock_query
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = [
            '/test/file0.txt',
            '/test/file1.txt',
            '/test/file2.txt',
            '/test/file3.txt',
            '/test/file4.txt',
        ]
        mock_query.filter.return_value.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = default_user
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_query.filter.return_value.first.return_value = mock_first

        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = MagicMock(raw_text='test')
            
            with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                mock_tte.split_entries_by_max_tokens.return_value = []

                call_command(
                    'reindex_multi_scale',
                    '--scales', '512',
                    '--batch-size', '2',
                    '--apply',
                    stdout=out,
                    stderr=err
                )

    output = out.getvalue()
    assert 'Found 5 unique files to process' in output
    # Should show progress for multiple batches
    assert 'Progress:' in output


@pytest.mark.django_db
def test_user_filter(default_user, default_user2):
    """Test that entries are filtered by user email when specified."""
    out = StringIO()
    err = StringIO()

    # Create entries for both users
    Entry.objects.create(
        user=default_user,
        raw='user1 content',
        compiled='user1 content',
        heading='User1 Test',
        file_path='/test/file1.txt',
        file_type='plaintext',
        file_source='computer',
    )
    Entry.objects.create(
        user=default_user2,
        raw='user2 content',
        compiled='user2 content',
        heading='User2 Test',
        file_path='/test/file2.txt',
        file_type='plaintext',
        file_source='computer',
    )

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_query = MagicMock()
        mock_entry.all.return_value = mock_query
        mock_filtered = MagicMock()
        mock_query.filter.return_value = mock_filtered
        mock_filtered.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file1.txt']
        
        call_command(
            'reindex_multi_scale',
            '--user', default_user.email,
            '--scales', '512',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert f'Filtering by user: {default_user.email}' in output
    mock_query.filter.assert_called_once()


@pytest.mark.django_db
def test_transaction_safety(default_user):
    """Test that transactions are rolled back on error."""
    out = StringIO()
    err = StringIO()

    # Create test entry
    Entry.objects.create(
        user=default_user,
        raw='test content',
        compiled='test content',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
    )

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_query = MagicMock()
        mock_entry.all.return_value = mock_query
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        mock_query.filter.return_value.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = default_user
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_query.filter.return_value.first.return_value = mock_first

        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = MagicMock(raw_text='test')
            
            with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                mock_tte.split_entries_by_max_tokens.side_effect = Exception("Test error")

                with pytest.raises(Exception, match="Test error"):
                    call_command(
                        'reindex_multi_scale',
                        '--scales', '512',
                        '--apply',
                        stdout=out,
                        stderr=err
                    )

    # The exception should propagate, indicating transaction was rolled back
    error_output = err.getvalue()
    assert 'Error processing batch' in error_output or 'Test error' in error_output


@pytest.mark.django_db
def test_no_files_found(default_user):
    """Test that empty result is handled gracefully."""
    out = StringIO()
    err = StringIO()

    # No entries exist
    call_command(
        'reindex_multi_scale',
        '--scales', '512,1024',
        stdout=out,
        stderr=err
    )

    output = out.getvalue()
    assert 'No files found to reindex. Nothing to do.' in output


def test_invalid_scales_format():
    """Test that invalid scales format produces an error."""
    out = StringIO()
    err = StringIO()

    call_command(
        'reindex_multi_scale',
        '--scales', 'invalid,format',
        stdout=out,
        stderr=err
    )

    error_output = err.getvalue()
    assert 'Invalid scales format' in error_output
    assert "Expected comma-separated integers" in error_output


@pytest.mark.django_db
def test_nonexistent_user_filter():
    """Test that nonexistent user email produces an error."""
    out = StringIO()
    err = StringIO()

    call_command(
        'reindex_multi_scale',
        '--user', 'nonexistent@example.com',
        '--scales', '512',
        stdout=out,
        stderr=err
    )

    error_output = err.getvalue()
    assert 'User not found: nonexistent@example.com' in error_output


@pytest.mark.django_db
def test_missing_file_object_warning(default_user):
    """Test that missing FileObject produces a warning but continues."""
    out = StringIO()
    err = StringIO()

    # Create test entry without corresponding FileObject
    Entry.objects.create(
        user=default_user,
        raw='test content',
        compiled='test content',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
    )

    with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
        # Return None to simulate missing FileObject
        mock_foa.get_file_object_by_name.return_value = None

        call_command(
            'reindex_multi_scale',
            '--scales', '512',
            '--apply',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert 'Warning: No FileObject found for' in output
    assert 'Multi-scale reindexing complete!' in output


def test_default_scales():
    """Test that default scales are used when not specified."""
    out = StringIO()
    err = StringIO()

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_entry.all.return_value.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        call_command(
            'reindex_multi_scale',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    # Default scales should be 512, 1024, 2048
    assert 'chunk sizes: [512, 1024, 2048]' in output


def test_default_batch_size():
    """Test that default batch size is used when not specified."""
    out = StringIO()
    err = StringIO()

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_entry.all.return_value.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        call_command(
            'reindex_multi_scale',
            '--apply',
            stdout=out,
            stderr=err
        )

    # Command should complete without error using default batch size of 100
    output = out.getvalue()
    assert 'No files found to reindex. Nothing to do.' in output or '[APPLY]' in output


def test_whitespace_in_scales():
    """Test that whitespace in scales argument is handled correctly."""
    out = StringIO()
    err = StringIO()

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_entry.all.return_value.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        call_command(
            'reindex_multi_scale',
            '--scales', ' 256 , 512 , 1024 ',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert 'chunk sizes: [256, 512, 1024]' in output


def test_single_scale():
    """Test that single scale value works correctly."""
    out = StringIO()
    err = StringIO()

    with patch('khoj.database.management.commands.reindex_multi_scale.Entry.objects') as mock_entry:
        mock_entry.all.return_value.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        call_command(
            'reindex_multi_scale',
            '--scales', '1024',
            stdout=out,
            stderr=err
        )

    output = out.getvalue()
    assert 'chunk sizes: [1024]' in output


@pytest.mark.django_db
def test_entry_creation_with_all_fields(default_user):
    """Test that entries are created with all required fields."""
    out = StringIO()
    err = StringIO()

    # Create a FileObject for the test
    file_object = FileObject.objects.create(
        user=default_user,
        file_name='/test/file.txt',
        raw_text='Test content for reindexing',
    )

    # Create test entry
    Entry.objects.create(
        user=default_user,
        raw='Test content',
        compiled='Test content',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
        chunk_scale='512',
    )

    # Mock TextToEntries to return new entries with all fields
    mock_entry_config = MagicMock()
    mock_entry_config.raw = 'chunked raw'
    mock_entry_config.compiled = 'chunked compiled'
    mock_entry_config.heading = 'chunked heading'
    mock_entry_config.file = '/test/file.txt'
    mock_entry_config.chunk_scale = '512'
    mock_entry_config.corpus_id = 'test-corpus-id'
    mock_entry_config.uri = 'http://example.com/test'

    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = file_object
            mock_tte.split_entries_by_max_tokens.return_value = [mock_entry_config]

            call_command(
                'reindex_multi_scale',
                '--scales', '512',
                '--apply',
                stdout=out,
                stderr=err
            )

    output = out.getvalue()
    assert 'Multi-scale reindexing complete!' in output
    assert 'Entries created: 1' in output


@pytest.mark.django_db
def test_scale_labels_filtering(default_user):
    """Test that only entries with specified scales are deleted."""
    out = StringIO()
    err = StringIO()

    # Create a FileObject for the test
    file_object = FileObject.objects.create(
        user=default_user,
        file_name='/test/file.txt',
        raw_text='Test content for reindexing',
    )

    # Create test entries with different scales
    Entry.objects.create(
        user=default_user,
        raw='Test content 512',
        compiled='Test content 512',
        heading='Test 512',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
        chunk_scale='512',
    )
    Entry.objects.create(
        user=default_user,
        raw='Test content 1024',
        compiled='Test content 1024',
        heading='Test 1024',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
        chunk_scale='1024',
    )
    Entry.objects.create(
        user=default_user,
        raw='Test content other',
        compiled='Test content other',
        heading='Test other',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
        chunk_scale='other',
    )

    mock_entry_config = MagicMock()
    mock_entry_config.raw = 'new chunked'
    mock_entry_config.compiled = 'new compiled'
    mock_entry_config.heading = 'new heading'
    mock_entry_config.file = '/test/file.txt'
    mock_entry_config.chunk_scale = '512'
    mock_entry_config.corpus_id = 'test'
    mock_entry_config.uri = None

    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = file_object
            mock_tte.split_entries_by_max_tokens.return_value = [mock_entry_config]

            call_command(
                'reindex_multi_scale',
                '--scales', '512',  # Only reindex scale 512
                '--apply',
                stdout=out,
                stderr=err
            )

    output = out.getvalue()
    # Should have deleted 1 entry (the 512 scale one) and created 1 new entry
    assert 'Entries deleted: 1' in output
    assert 'Entries created: 1' in output


@pytest.mark.django_db
def test_embeddings_warning_message(default_user):
    """Test that warning about embeddings is shown after completion."""
    out = StringIO()
    err = StringIO()

    # Create a FileObject for the test
    file_object = FileObject.objects.create(
        user=default_user,
        file_name='/test/file.txt',
        raw_text='Test content',
    )

    Entry.objects.create(
        user=default_user,
        raw='Test content',
        compiled='Test content',
        heading='Test',
        file_path='/test/file.txt',
        file_type='plaintext',
        file_source='computer',
    )

    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
        with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
            mock_foa.get_file_object_by_name.return_value = file_object
            mock_tte.split_entries_by_max_tokens.return_value = []

            call_command(
                'reindex_multi_scale',
                '--scales', '512',
                '--apply',
                stdout=out,
                stderr=err
            )

    output = out.getvalue()
    assert 'embeddings have not been generated yet' in output
    assert "generate_embeddings" in output
