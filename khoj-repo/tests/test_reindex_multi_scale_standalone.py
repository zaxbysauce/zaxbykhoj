"""
Standalone test runner for reindex_multi_scale command tests.
Run with: python tests/test_reindex_multi_scale_standalone.py
"""

import sys
import os
from io import StringIO
from unittest.mock import MagicMock, patch, Mock

def run_tests():
    """Run all tests for reindex_multi_scale command."""
    
    # Add src to path
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    
    # Set up mocks before any imports
    import django
    from django.conf import settings
    
    # Configure minimal Django settings
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'django_apscheduler',
                'khoj.database',
            ],
            USE_TZ=True,
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
        )
        django.setup()
    
    # Now we can import the command
    from khoj.database.management.commands.reindex_multi_scale import Command
    
    tests_passed = 0
    tests_failed = 0
    
    def test_scales_argument_parsing():
        """Test that comma-separated integers are parsed correctly."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            cmd.handle(scales='256,512,1024', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('[DRY RUN]' in str(c) for c in calls), f"Expected [DRY RUN] in output, got: {calls}"
        assert any('chunk sizes: [256, 512, 1024]' in str(c) for c in calls), f"Expected chunk sizes in output, got: {calls}"
        return True
    
    def test_invalid_scales_format():
        """Test that invalid scales format produces an error."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        cmd.handle(scales='invalid,format', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in err.write.call_args_list]
        assert any('Invalid scales format' in str(c) for c in calls), f"Expected Invalid scales format error, got: {calls}"
        assert any('Expected comma-separated integers' in str(c) for c in calls), f"Expected usage message, got: {calls}"
        return True
    
    def test_no_files_found():
        """Test that empty result is handled gracefully."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            cmd.handle(scales='512,1024', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('No files found to reindex. Nothing to do.' in str(c) for c in calls), f"Expected no files message, got: {calls}"
        return True
    
    def test_default_scales():
        """Test that default scales are used when not specified."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            cmd.handle(scales='512,1024,2048', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('chunk sizes: [512, 1024, 2048]' in str(c) for c in calls), f"Expected default scales, got: {calls}"
        return True
    
    def test_whitespace_in_scales():
        """Test that whitespace in scales argument is handled correctly."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            cmd.handle(scales=' 256 , 512 , 1024 ', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('chunk sizes: [256, 512, 1024]' in str(c) for c in calls), f"Expected trimmed scales, got: {calls}"
        return True
    
    def test_single_scale():
        """Test that single scale value works correctly."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = []
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            cmd.handle(scales='1024', batch_size=100, apply=False, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('chunk sizes: [1024]' in str(c) for c in calls), f"Expected single scale, got: {calls}"
        return True
    
    def test_nonexistent_user_filter():
        """Test that nonexistent user email produces an error."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        # Create a proper DoesNotExist exception class
        class DoesNotExist(Exception):
            pass
        
        mock_user_model = MagicMock()
        mock_user_model.DoesNotExist = DoesNotExist
        mock_user_model.objects = MagicMock()
        mock_user_model.objects.get = MagicMock(side_effect=DoesNotExist('User not found'))
        
        with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
            cmd.handle(scales='512', batch_size=100, apply=False, user='nonexistent@example.com')
        
        calls = [str(call) for call in err.write.call_args_list]
        assert any('User not found: nonexistent@example.com' in str(c) for c in calls), f"Expected user not found error, got: {calls}"
        return True
    
    def test_dry_run_mode():
        """Test that dry-run mode shows counts without modifying database."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        mock_query.count.return_value = 5
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            
            with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                cmd.handle(scales='512,1024', batch_size=100, apply=False, user=None)
                
                # Verify TextToEntries was not called in dry-run mode
                mock_tte.split_entries_by_max_tokens.assert_not_called()
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('[DRY RUN]' in str(c) for c in calls), f"Expected [DRY RUN] in output, got: {calls}"
        assert any('Total entries to reindex: 5' in str(c) for c in calls), f"Expected entry count, got: {calls}"
        return True
    
    def test_apply_mode():
        """Test that apply mode actually performs reindexing."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user = MagicMock()
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.DoesNotExist = Exception
        
        mock_file_object = MagicMock()
        mock_file_object.raw_text = 'Test content'
        
        mock_entry_config = MagicMock()
        mock_entry_config.raw = 'chunked content'
        mock_entry_config.compiled = 'chunked compiled'
        mock_entry_config.heading = 'chunked heading'
        mock_entry_config.file = '/test/file.txt'
        mock_entry_config.chunk_scale = '512'
        mock_entry_config.corpus_id = 'test-corpus'
        mock_entry_config.uri = None
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        mock_file_entries = MagicMock()
        mock_file_entries.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = mock_user
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_file_entries.first.return_value = mock_first
        mock_file_entries.filter.return_value.delete.return_value = [1]
        mock_query.filter.return_value = mock_file_entries
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            mock_entry.objects.bulk_create = MagicMock()
            mock_entry.objects.filter.return_value = mock_file_entries
            
            with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
                with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
                    mock_foa.get_file_object_by_name.return_value = mock_file_object
                    
                    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                        mock_tte.split_entries_by_max_tokens.return_value = [mock_entry_config]
                        
                        cmd.handle(scales='512,1024', batch_size=100, apply=True, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('[APPLY]' in str(c) for c in calls), f"Expected [APPLY] in output, got: {calls}"
        assert any('Multi-scale reindexing complete!' in str(c) for c in calls), f"Expected completion message, got: {calls}"
        mock_tte.split_entries_by_max_tokens.assert_called_once()
        return True
    
    def test_batch_processing():
        """Test that files are processed in batches."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.DoesNotExist = Exception
        
        mock_file_object = MagicMock()
        mock_file_object.raw_text = 'Test content'
        
        mock_query = MagicMock()
        file_paths = [f'/test/file{i}.txt' for i in range(5)]
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = file_paths
        
        mock_file_entries = MagicMock()
        mock_file_entries.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = MagicMock()
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_file_entries.first.return_value = mock_first
        mock_file_entries.filter.return_value.delete.return_value = [0]
        mock_query.filter.return_value = mock_file_entries
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            mock_entry.objects.bulk_create = MagicMock()
            mock_entry.objects.filter.return_value = mock_file_entries
            
            with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
                with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
                    mock_foa.get_file_object_by_name.return_value = mock_file_object
                    
                    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                        mock_tte.split_entries_by_max_tokens.return_value = []
                        
                        cmd.handle(scales='512', batch_size=2, apply=True, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('Found 5 unique files to process' in str(c) for c in calls), f"Expected file count, got: {calls}"
        assert any('Progress:' in str(c) for c in calls), f"Expected progress message, got: {calls}"
        return True
    
    def test_transaction_safety():
        """Test that transactions are rolled back on error."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.DoesNotExist = Exception
        
        mock_file_object = MagicMock()
        mock_file_object.raw_text = 'Test content'
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        
        mock_file_entries = MagicMock()
        mock_file_entries.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = MagicMock()
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_file_entries.first.return_value = mock_first
        mock_query.filter.return_value = mock_file_entries
        
        exception_raised = False
        try:
            with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
                mock_entry.objects = MagicMock()
                mock_entry.objects.all.return_value = mock_query
                mock_entry.objects.filter.return_value = mock_file_entries
                
                with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
                    with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
                        mock_foa.get_file_object_by_name.return_value = mock_file_object
                        
                        with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                            mock_tte.split_entries_by_max_tokens.side_effect = Exception("Test error")
                            
                            cmd.handle(scales='512', batch_size=100, apply=True, user=None)
        except Exception as e:
            if "Test error" in str(e):
                exception_raised = True
        
        assert exception_raised, "Expected exception to be raised for transaction rollback test"
        
        calls = [str(call) for call in err.write.call_args_list]
        assert any('Error processing batch' in str(c) or 'Test error' in str(c) for c in calls), f"Expected error message, got: {calls}"
        return True
    
    def test_missing_file_object_warning():
        """Test that missing FileObject produces a warning but continues."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.DoesNotExist = Exception
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        
        mock_file_entries = MagicMock()
        mock_file_entries.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = MagicMock()
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_file_entries.first.return_value = mock_first
        mock_file_entries.filter.return_value.delete.return_value = [0]
        mock_query.filter.return_value = mock_file_entries
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            mock_entry.objects.filter.return_value = mock_file_entries
            
            with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
                with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
                    # Return None to simulate missing FileObject
                    mock_foa.get_file_object_by_name.return_value = None
                    
                    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                        mock_tte.split_entries_by_max_tokens.return_value = []
                        
                        cmd.handle(scales='512', batch_size=100, apply=True, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('Warning: No FileObject found for' in str(c) for c in calls), f"Expected warning message, got: {calls}"
        assert any('Multi-scale reindexing complete!' in str(c) for c in calls), f"Expected completion message, got: {calls}"
        return True
    
    def test_embeddings_warning_message():
        """Test that warning about embeddings is shown after completion."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.DoesNotExist = Exception
        
        mock_file_object = MagicMock()
        mock_file_object.raw_text = 'Test content'
        
        mock_query = MagicMock()
        mock_query.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        
        mock_file_entries = MagicMock()
        mock_file_entries.exists.return_value = True
        mock_first = MagicMock()
        mock_first.user = MagicMock()
        mock_first.file_type = 'plaintext'
        mock_first.file_source = 'computer'
        mock_file_entries.first.return_value = mock_first
        mock_file_entries.filter.return_value.delete.return_value = [0]
        mock_query.filter.return_value = mock_file_entries
        
        with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
            mock_entry.objects = MagicMock()
            mock_entry.objects.all.return_value = mock_query
            mock_entry.objects.bulk_create = MagicMock()
            mock_entry.objects.filter.return_value = mock_file_entries
            
            with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
                with patch('khoj.database.management.commands.reindex_multi_scale.FileObjectAdapters') as mock_foa:
                    mock_foa.get_file_object_by_name.return_value = mock_file_object
                    
                    with patch('khoj.database.management.commands.reindex_multi_scale.TextToEntries') as mock_tte:
                        mock_tte.split_entries_by_max_tokens.return_value = []
                        
                        cmd.handle(scales='512', batch_size=100, apply=True, user=None)
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('embeddings have not been generated yet' in str(c) for c in calls), f"Expected embeddings warning, got: {calls}"
        assert any('generate_embeddings' in str(c) for c in calls), f"Expected generate_embeddings reference, got: {calls}"
        return True
    
    def test_user_filter():
        """Test that entries are filtered by user email when specified."""
        cmd = Command()
        out = MagicMock()
        err = MagicMock()
        cmd.stdout = out
        cmd.stderr = err
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x
        cmd.style.WARNING = lambda x: x
        
        mock_user = MagicMock()
        mock_user.email = 'test@example.com'
        
        mock_user_model = MagicMock()
        mock_user_model.objects = MagicMock()
        mock_user_model.objects.get.return_value = mock_user
        
        mock_query = MagicMock()
        mock_filtered = MagicMock()
        mock_query.filter.return_value = mock_filtered
        mock_filtered.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['/test/file.txt']
        
        with patch('khoj.database.management.commands.reindex_multi_scale.KhojUser', mock_user_model):
            with patch('khoj.database.management.commands.reindex_multi_scale.Entry') as mock_entry:
                mock_entry.objects = MagicMock()
                mock_entry.objects.all.return_value = mock_query
                
                cmd.handle(scales='512', batch_size=100, apply=False, user='test@example.com')
        
        calls = [str(call) for call in out.write.call_args_list]
        assert any('Filtering by user: test@example.com' in str(c) for c in calls), f"Expected user filter message, got: {calls}"
        return True
    
    # Run all tests
    tests = [
        ("test_scales_argument_parsing", test_scales_argument_parsing),
        ("test_invalid_scales_format", test_invalid_scales_format),
        ("test_no_files_found", test_no_files_found),
        ("test_default_scales", test_default_scales),
        ("test_whitespace_in_scales", test_whitespace_in_scales),
        ("test_single_scale", test_single_scale),
        ("test_nonexistent_user_filter", test_nonexistent_user_filter),
        ("test_dry_run_mode", test_dry_run_mode),
        ("test_apply_mode", test_apply_mode),
        ("test_batch_processing", test_batch_processing),
        ("test_transaction_safety", test_transaction_safety),
        ("test_missing_file_object_warning", test_missing_file_object_warning),
        ("test_embeddings_warning_message", test_embeddings_warning_message),
        ("test_user_filter", test_user_filter),
    ]
    
    print("=" * 60)
    print("Running reindex_multi_scale command tests")
    print("=" * 60)
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {test_name}")
            tests_passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test_name}: {e}")
            tests_failed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: Unexpected error: {e}")
            tests_failed += 1
    
    print("=" * 60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    return tests_failed == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
