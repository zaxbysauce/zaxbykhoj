# Critical Issues Fix Plan

## Overview
Database schema and code issues identified blocking RAG Enhancement functionality.

## Issues and Fixes

### Issue 1: Missing Database Schema Columns
**Problem**: Model fields exist but database columns missing

**Fix 1a: Create Migration 0105 for SearchModelConfig**
```python
# khoj-repo/src/khoj/database/migrations/0105_add_hybrid_fields.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("database", "0104_ldap_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchmodelconfig",
            name="hybrid_alpha",
            field=models.FloatField(default=0.6),
        ),
        migrations.AddField(
            model_name="searchmodelconfig",
            name="hybrid_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
```

**Fix 1b: Create Migration 0106 for KhojUser ldap_dn**
```python
# khoj-repo/src/khoj/database/migrations/0106_add_ldap_dn.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("database", "0105_add_hybrid_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="khojuser",
            name="ldap_dn",
            field=models.CharField(max_length=255, null=True, blank=True, default=None),
        ),
    ]
```

**Fix 1c: Make Entry.embeddings nullable**
```python
# khoj-repo/src/khoj/database/migrations/0107_alter_entry_embeddings.py
from django.db import migrations
import pgvector.django

class Migration(migrations.Migration):
    dependencies = [
        ("database", "0106_add_ldap_dn"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entry",
            name="embeddings",
            field=pgvector.django.VectorField(dimensions=None, null=True, blank=True),
        ),
    ]
```

### Issue 2: Migration Dependency Error
**Problem**: 0104 references non-existent 0103

**Fix**: Update 0104 dependencies
```python
# Change in khoj-repo/src/khoj/database/migrations/0104_ldap_config.py
dependencies = [
    ("database", "0102_add_chunk_scale"),  # Was: 0103_add_ldap_dn_to_user
]
```

### Issue 3: pyproject.toml Version Error
**Problem**: hatch-vcs requires git tags

**Fix**: Use static version
```toml
# khoj-repo/pyproject.toml
[build-system]
requires = ["hatchling"]  # Remove: "hatch-vcs"
build-backend = "hatchling.build"

[project]
name = "khoj"
version = "2.0.0"  # Add: static version
# Remove: dynamic = ["version"]
```

### Issue 4: Entry.save() Not Working
**Problem**: Entry.save() doesn't call super().save()

**Fix**: Add super().save() call
```python
# khoj-repo/src/khoj/database/models/__init__.py
def save(self, *args, **kwargs):
    if self.user and self.agent:
        raise ValidationError("An Entry cannot be associated with both a user and an agent.")
    super().save(*args, **kwargs)  # ADD THIS LINE
```

### Issue 5: Embedding Dimension Mismatch
**Problem**: VectorField(dimensions=None) may cause issues

**Fix**: Set dimensions explicitly (if known) or keep nullable
```python
# In migration 0107, dimensions=None with null=True is correct for variable dimensions
# For fixed dimensions (e.g., 768), use:
# field=pgvector.django.VectorField(dimensions=768, null=True, blank=True)
```

### Issue 6: Migrations 0100-0102 Missing Fields
**Problem**: SearchModelConfig fields not in 0100

**Fix**: Already addressed in Issue 1a (Migration 0105)

## Implementation Order

1. **Fix Entry.save()** - Code change (Priority 1)
2. **Fix pyproject.toml** - Build fix (Priority 1)
3. **Fix migration 0104 dependency** - Migration fix (Priority 2)
4. **Create migration 0105** - Hybrid fields (Priority 2)
5. **Create migration 0106** - LDAP dn field (Priority 2)
6. **Create migration 0107** - Embeddings nullable (Priority 2)

## Testing After Fix

1. Run migrations: `python manage.py migrate`
2. Test Entry.save(): Create entry, verify ID returned
3. Test SearchModelConfig: Verify hybrid fields accessible
4. Run benchmark: Verify MAP@10 > 0
