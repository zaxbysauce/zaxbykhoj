# Migration Rollback Documentation

## Prerequisites

Before running any commands in this document:

1. **Navigate to the repository root:**
   ```bash
   cd khoj-repo
   ```

2. **PostgreSQL Credentials:** The `psql` commands below require valid PostgreSQL credentials. Ensure you have:
   - Database username (replace `username` in commands)
   - Database name (replace `database_name` in commands)
   - Proper permissions to execute DDL operations

   You may need to add `-h localhost` or `-p 5432` depending on your setup.

## Table of Contents
1. [Overview](#overview)
2. [Pre-Rollback Checklist](#pre-rollback-checklist)
3. [Rollback Procedures](#rollback-procedures)
4. [Complete Rollback (All 3 Migrations)](#complete-rollback-all-3-migrations)
5. [Post-Rollback Verification](#post-rollback-verification)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### What Migrations Are Covered

This document covers rollback procedures for the following RAG (Retrieval-Augmented Generation) enhancement migrations:

| Migration | File | Description |
|-----------|------|-------------|
| **0100** | `0100_add_search_vector.py` | Adds PostgreSQL full-text search vector field with GIN index |
| **0101** | `0101_add_context_summary.py` | Adds context summary field for LLM-generated summaries |
| **0102** | `0102_add_chunk_scale.py` | Adds chunk scale field for multi-scale chunking support |

### What Each Migration Adds

#### 0100_add_search_vector
- **Field Added:** `search_vector` (SearchVectorField)
- **Index Added:** `entry_search_vector_gin_idx` (GIN index)
- **Purpose:** Enables efficient PostgreSQL full-text search on Entry content
- **Dependencies:** Depends on migration 0099_usermemory

#### 0101_add_context_summary
- **Field Added:** `context_summary` (TextField)
- **Purpose:** Stores LLM-generated context summaries for entry chunks to improve retrieval relevance
- **Dependencies:** Depends on migration 0100_add_search_vector

#### 0102_add_chunk_scale
- **Field Added:** `chunk_scale` (CharField, max_length=16)
- **Purpose:** Supports multi-scale chunking strategy (512, 1024, 2048, default)
- **Dependencies:** Depends on migration 0101_add_context_summary

### Why Rollback Might Be Needed

Common scenarios requiring rollback:

1. **Performance Issues:** Search vector updates causing excessive database load
2. **Storage Concerns:** Context summary generation consuming too much disk space
3. **Feature Deprecation:** Multi-scale chunking not providing expected benefits
4. **Bug Discovery:** Issues discovered in production after deployment
5. **Rollback Testing:** Testing rollback procedures in staging environment
6. **Version Compatibility:** Need to downgrade to earlier application version

---

## Pre-Rollback Checklist

### 1. Backup Database

**Critical:** Always create a full database backup before rolling back migrations.

```bash
# Create timestamped backup
pg_dump -U username -h localhost -d database_name > backup_$(date +%Y%m%d_%H%M%S).sql

# For larger databases, use compressed backup
pg_dump -U username -h localhost -d database_name | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Verify backup integrity:**
```bash
# Check backup file size
ls -lh backup_*.sql*

# For uncompressed backups, verify structure
head -n 50 backup_$(date +%Y%m%d).sql
```

### 2. Verify Current Migration State

```bash
# Check current migration state
python manage.py showmigrations database

# Expected output if all three migrations applied:
# [X] 0099_usermemory
# [X] 0100_add_search_vector
# [X] 0101_add_context_summary
# [X] 0102_add_chunk_scale
```

### 3. Check for Dependent Features

**Verify no active code depends on these fields:**

```bash
# Search for code using search_vector
grep -r "search_vector" --include="*.py" src/

# Search for code using context_summary
grep -r "context_summary" --include="*.py" src/

# Search for code using chunk_scale
grep -r "chunk_scale" --include="*.py" src/

# Check for database queries using these fields
grep -r "Entry.objects.filter.*search_vector" --include="*.py" src/
grep -r "Entry.objects.filter.*context_summary" --include="*.py" src/
grep -r "Entry.objects.filter.*chunk_scale" --include="*.py" src/
```

### 4. Document Current Row Counts

```bash
# Get row counts for verification after rollback
python manage.py shell -c "from khoj.database.models import Entry; print(f'Entry count: {Entry.objects.count()}')"

# Alternative using psql
psql -U username -d database_name -c "SELECT COUNT(*) FROM database_entry;"
```

### 5. Check Application Status

```bash
# Ensure no active migrations are running
ps aux | grep migrate

# Check application health
python manage.py check

# Verify database connectivity
psql -U username -d database_name -c "SELECT 1;"
```

---

## Rollback Procedures

### Rollback Migration 0102_add_chunk_scale

**Target:** Remove the `chunk_scale` field from Entry model

#### Command to Rollback

```bash
# Rollback to migration 0101 (removes 0102)
python manage.py migrate database 0101
```

#### What Data Is Affected

- **Column Removed:** `chunk_scale` (CharField, max_length=16)
- **Data Lost:** All values in `chunk_scale` column (e.g., '512', '1024', '2048', 'default')
- **Rows Affected:** All rows in `database_entry` table
- **Indexes:** No indexes on this field to remove

#### Verification Steps

```bash
# Verify migration state
python manage.py showmigrations database

# Verify column removal
psql -U username -d database_name -c "\d database_entry" | grep chunk_scale
# Expected: No output (column should not exist)

# Alternative verification
psql -U username -d database_name -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'database_entry' AND column_name = 'chunk_scale';"
# Expected: Empty result set

# Verify row count unchanged
psql -U username -d database_name -c "SELECT COUNT(*) FROM database_entry;"
```

---

### Rollback Migration 0101_add_context_summary

**Target:** Remove the `context_summary` field from Entry model

#### Command to Rollback

```bash
# Rollback to migration 0100 (removes 0101)
python manage.py migrate database 0100
```

#### What Data Is Affected

- **Column Removed:** `context_summary` (TextField)
- **Data Lost:** All LLM-generated context summaries stored in the column
- **Rows Affected:** All rows in `database_entry` table
- **Indexes:** No indexes on this field to remove

#### Verification Steps

```bash
# Verify migration state
python manage.py showmigrations database

# Verify column removal
psql -U username -d database_name -c "\d database_entry" | grep context_summary
# Expected: No output (column should not exist)

# Verify row count unchanged
psql -U username -d database_name -c "SELECT COUNT(*) FROM database_entry;"
```

---

### Rollback Migration 0100_add_search_vector

**Target:** Remove the `search_vector` field and GIN index from Entry model

#### Command to Rollback

```bash
# Rollback to migration 0099 (removes 0100)
python manage.py migrate database 0099
```

#### What Data Is Affected

- **Column Removed:** `search_vector` (SearchVectorField)
- **Index Removed:** `entry_search_vector_gin_idx` (GIN index)
- **Data Lost:** All computed search vectors for full-text search
- **Rows Affected:** All rows in `database_entry` table
- **Performance Impact:** Full-text search queries will no longer use GIN index

#### Verification Steps

```bash
# Verify migration state
python manage.py showmigrations database

# Verify column removal
psql -U username -d database_name -c "\d database_entry" | grep search_vector
# Expected: No output (column should not exist)

# Verify index removal
psql -U username -d database_name -c "\di" | grep entry_search_vector_gin_idx
# Expected: No output (index should not exist)

# Verify row count unchanged
psql -U username -d database_name -c "SELECT COUNT(*) FROM database_entry;"
```

---

## Complete Rollback (All 3 Migrations)

### Single Command to Rollback All

```bash
# Rollback all three migrations at once (to 0099)
python manage.py migrate database 0099
```

This single command will execute rollbacks in reverse order:
1. Rollback 0102_add_chunk_scale
2. Rollback 0101_add_context_summary
3. Rollback 0100_add_search_vector

### Expected Output

```
Operations to perform:
  Target specific migration: 0099_usermemory, from database
Running migrations:
  Reversing 0102.0102_add_chunk_scale... OK
  Reversing 0101.0101_add_context_summary... OK
  Reversing 0100.0100_add_search_vector... OK
```

### Verification That All Columns Removed

```bash
# Check that all three columns are removed
psql -U username -d database_name -c "\d database_entry" | grep -E "search_vector|context_summary|chunk_scale"
# Expected: No output (all columns should be removed)

# Alternative: Query information_schema
psql -U username -d database_name -c "
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'database_entry'
AND column_name IN ('search_vector', 'context_summary', 'chunk_scale');
"
# Expected: Empty result set
```

### Row Count Verification

```bash
# Verify all rows preserved
psql -U username -d database_name -c "SELECT COUNT(*) FROM database_entry;"

# Compare with pre-rollback count (should match)
```

### Verify No Orphaned Indexes

```bash
# Check for any remaining indexes related to rolled back migrations
psql -U username -d database_name -c "\di" | grep -E "search_vector|context_summary|chunk_scale"
# Expected: No output
```

---

## Post-Rollback Verification

### 1. Verify Column Removal

```bash
# Complete verification of all columns
psql -U username -d database_name <<'EOF'
\echo '=== Checking for removed columns ==='
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'database_entry'
AND column_name IN ('search_vector', 'context_summary', 'chunk_scale');
EOF

# Expected output: No rows
```

### 2. Verify Row Counts Preserved

```bash
# Get current row count
python manage.py shell -c "
from khoj.database.models import Entry
count = Entry.objects.count()
print(f'Entry table row count: {count}')
"

# Should match pre-rollback count
```

### 3. Verify Query Results Unchanged

```bash
# Test basic Entry queries still work
python manage.py shell -c "
from khoj.database.models import Entry

# Test basic query
entry = Entry.objects.first()
if entry:
    print(f'Success: Retrieved entry id={entry.id}')
    print(f'  - raw: {entry.raw[:50]}...' if hasattr(entry, 'raw') and entry.raw else '  - raw: None')
    print(f'  - embeddings present: {bool(entry.embeddings)}' if hasattr(entry, 'embeddings') else '  - embeddings: N/A')
else:
    print('No entries found (expected if database is empty)')
"
```

### 4. Verify Application Health

```bash
# Run Django system checks
python manage.py check

# Expected output:
# System check identified no issues (0 silenced).
```

### 5. Verify Migration State

```bash
# Final migration state check
python manage.py showmigrations database

# Expected output:
# [X] 0099_usermemory
# [ ] 0100_add_search_vector
# [ ] 0101_add_context_summary
# [ ] 0102_add_chunk_scale
```

### 6. Re-apply If Needed

If you need to re-apply the migrations after rollback:

```bash
# Apply all three migrations
python manage.py migrate database

# Or apply individually:
python manage.py migrate database 0100  # Apply 0100 only
python manage.py migrate database 0101  # Apply 0100-0101
python manage.py migrate database 0102  # Apply 0100-0102
```

**Note:** Re-applying will recreate the columns with **default values** (null/empty). Previously stored context summaries and search vectors will need to be regenerated.

---

## Troubleshooting

### Common Issues

#### Issue 1: Migration Dependency Error

**Symptom:**
```
django.db.migrations.exceptions.InconsistentMigrationHistory: 
Migration database.0103_something is applied before its dependency database.0102_add_chunk_scale on database 'default'.
```

**Cause:** A newer migration depends on one being rolled back.

**Solution:**
```bash
# Check migration dependencies
python manage.py showmigrations database

# Rollback to the newest migration that doesn't depend on target
python manage.py migrate database 0099
```

#### Issue 2: Active Queries Blocking Migration

**Symptom:**
```
django.db.utils.OperationalError: cannot ALTER TABLE "database_entry" because it has pending trigger events
```

**Solution:**
```bash
# Identify blocking queries
psql -U username -d database_name -c "
SELECT pid, state, query
FROM pg_stat_activity
WHERE datname = current_database()
AND state = 'active';
"

# Terminate blocking queries (if safe to do so)
psql -U username -d database_name -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = current_database()
AND state = 'active'
AND query LIKE '%database_entry%';
"

# Retry rollback
python manage.py migrate database 0099
```

#### Issue 3: Permission Denied

**Symptom:**
```
django.db.utils.InsufficientPrivilege: must be owner of table database_entry
```

**Solution:**
```bash
# Grant necessary permissions
psql -U username -d database_name -c "ALTER TABLE database_entry OWNER TO current_user;"

# Or run migrate with appropriate database user
python manage.py migrate database 0099 --database=default
```

#### Issue 4: Column Still Exists After Rollback

**Symptom:** Migration reports success but column still visible.

**Solution:**
```bash
# Force migration state (use with caution!)
python manage.py migrate database 0099 --fake

# Manually drop column if necessary
psql -U username -d database_name -c "ALTER TABLE database_entry DROP COLUMN IF EXISTS chunk_scale;"
psql -U username -d database_name -c "ALTER TABLE database_entry DROP COLUMN IF EXISTS context_summary;"
psql -U username -d database_name -c "ALTER TABLE database_entry DROP COLUMN IF EXISTS search_vector;"

# Verify
psql -U username -d database_name -c "\d database_entry"
```

### Recovery Procedures

#### Scenario 1: Partial Rollback Failure

If rollback fails partway through:

```bash
# 1. Check current state
python manage.py showmigrations database

# 2. Restore from backup if needed
psql -U username -d database_name < backup_YYYYMMDD_HHMMSS.sql

# 3. Retry complete rollback
python manage.py migrate database 0099
```

#### Scenario 2: Data Corruption During Rollback

```bash
# 1. Stop application
# 2. Restore from pre-rollback backup
psql -U username -d database_name < backup_YYYYMMDD_HHMMSS.sql

# 3. Verify restoration
python manage.py showmigrations database

# 4. Re-apply migrations if needed
python manage.py migrate database
```

#### Scenario 3: Application Code Still References Rolled-Back Fields

```bash
# Check logs for AttributeError or FieldError
tail -f /var/log/khoj/error.log

# Temporarily add compatibility layer or fix code
grep -r "chunk_scale\|context_summary\|search_vector" src/

# Fix offending code, then redeploy
```

### Emergency Contacts and Resources

- **Django Migrations Documentation:** https://docs.djangoproject.com/en/stable/topics/migrations/
- **PostgreSQL ALTER TABLE:** https://www.postgresql.org/docs/current/sql-altertable.html
- **Khoj Database Schema:** See `src/khoj/database/models/`

### Quick Reference Commands

```bash
# Check status
python manage.py showmigrations database

# Full rollback
python manage.py migrate database 0099

# Partial rollback (to 0101)
python manage.py migrate database 0101

# Re-apply all
python manage.py migrate database

# Backup
pg_dump -U user -d dbname > backup.sql

# Verify columns removed
psql -U username -d database_name -c "\d database_entry" | grep -E "search_vector|context_summary|chunk_scale"
```

---

## Appendix: Migration Chain

```
0099_usermemory
    ↓
0100_add_search_vector ──┐
    ↓                    │ Can rollback to here
0101_add_context_summary─┤
    ↓                    │ Can rollback to here  
0102_add_chunk_scale─────┘
```

### Rollback Paths

| From | To | Command |
|------|-----|---------|
| 0102 | 0101 | `python manage.py migrate database 0101` |
| 0102 | 0100 | `python manage.py migrate database 0100` |
| 0102 | 0099 | `python manage.py migrate database 0099` |
| 0101 | 0100 | `python manage.py migrate database 0100` |
| 0101 | 0099 | `python manage.py migrate database 0099` |
| 0100 | 0099 | `python manage.py migrate database 0099` |

---

*Document Version: 1.0*
*Last Updated: 2026-03-07*
*Applicable Migrations: 0100, 0101, 0102*
