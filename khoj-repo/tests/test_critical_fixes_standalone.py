"""
Critical Fixes Tests - Standalone version (no database required)

Tests for the following critical fixes:
1. Entry.save() Fix - Entry model definition verification
2. Migration Chain - Migrations 0100-0107 dependency validation
3. New Model Fields - SearchModelConfig hybrid fields, KhojUser ldap_dn, Entry.embeddings nullable
4. pyproject.toml - TOML syntax and version validation
"""

import os
import sys
import ast

# Try to import tomllib (Python 3.11+) or tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def get_project_root():
    """Get the project root directory."""
    return os.path.join(os.path.dirname(__file__), "..")


def test_pyproject_toml_syntax_is_valid():
    """Verify TOML syntax is valid."""
    if tomllib is None:
        print("SKIP: tomllib/tomli not available")
        return True

    pyproject_path = os.path.join(get_project_root(), "pyproject.toml")

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    # Verify basic structure
    assert "project" in config, "Missing [project] section"
    assert "build-system" in config, "Missing [build-system] section"
    print("PASS: TOML syntax is valid")
    return True


def test_version_is_set_correctly():
    """Verify version is set correctly in pyproject.toml."""
    if tomllib is None:
        print("SKIP: tomllib/tomli not available")
        return True

    pyproject_path = os.path.join(get_project_root(), "pyproject.toml")

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    # Verify version exists and is a valid semantic version
    version = config["project"]["version"]
    assert version is not None, "Version is None"
    assert isinstance(version, str), "Version should be a string"

    # Basic semantic version check (e.g., "2.0.0")
    version_parts = version.split(".")
    assert len(version_parts) >= 2, "Version should have at least major.minor"

    # Verify parts are numeric
    for part in version_parts:
        assert part.isdigit() or part.replace("-", "").isalnum(), f"Invalid version part: {part}"

    print(f"PASS: Version is set correctly: {version}")
    return True


def test_required_dependencies_present():
    """Verify required dependencies are present in pyproject.toml."""
    if tomllib is None:
        print("SKIP: tomllib/tomli not available")
        return True

    pyproject_path = os.path.join(get_project_root(), "pyproject.toml")

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = config["project"]["dependencies"]

    # Check for key dependencies
    required_deps = ["django", "pgvector", "psycopg2-binary"]
    for dep in required_deps:
        assert any(dep in d.lower() for d in dependencies), f"Required dependency {dep} not found"

    print("PASS: Required dependencies are present")
    return True


def test_migrations_0100_to_0107_exist():
    """Test that migrations 0100-0107 exist."""
    migration_files = [
        "0100_add_search_vector.py",
        "0101_add_context_summary.py",
        "0102_add_chunk_scale.py",
        "0103_add_ldap_dn_to_user.py",
        "0104_ldap_config.py",
        "0105_add_hybrid_fields.py",
        "0106_add_ldap_dn.py",
        "0107_alter_entry_embeddings.py",
    ]

    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    for migration_file in migration_files:
        file_path = os.path.join(migrations_dir, migration_file)
        assert os.path.exists(file_path), f"Migration file {migration_file} not found"

    print("PASS: All migration files 0100-0107 exist")
    return True


def test_0100_migration_dependencies():
    """Test 0100_add_search_vector dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0100_add_search_vector.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0099_usermemory")' in content, "Missing dependency on 0099_usermemory"
    assert "SearchVectorField" in content, "Missing SearchVectorField"
    assert "GinIndex" in content, "Missing GinIndex"

    print("PASS: 0100 migration has correct dependencies")
    return True


def test_0101_migration_dependencies():
    """Test 0101_add_context_summary dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0101_add_context_summary.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0100_add_search_vector")' in content, "Missing dependency on 0100"
    assert "context_summary" in content, "Missing context_summary field"

    print("PASS: 0101 migration has correct dependencies")
    return True


def test_0102_migration_dependencies():
    """Test 0102_add_chunk_scale dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0102_add_chunk_scale.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0101_add_context_summary")' in content, "Missing dependency on 0101"
    assert "chunk_scale" in content, "Missing chunk_scale field"

    print("PASS: 0102 migration has correct dependencies")
    return True


def test_0103_migration_dependencies():
    """Test 0103_add_ldap_dn_to_user dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0103_add_ldap_dn_to_user.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0102_add_chunk_scale")' in content, "Missing dependency on 0102"
    assert "ldap_dn" in content, "Missing ldap_dn field"
    assert "khojuser" in content.lower(), "Missing khojuser model reference"

    print("PASS: 0103 migration has correct dependencies")
    return True


def test_0104_migration_dependencies():
    """Test 0104_ldap_config dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0104_ldap_config.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies - 0104 should depend on 0103
    assert '("database", "0103_add_ldap_dn_to_user")' in content, "Missing dependency on 0103"
    assert "LdapConfig" in content, "Missing LdapConfig model"

    print("PASS: 0104 migration has correct dependencies")
    return True


def test_0105_migration_dependencies():
    """Test 0105_add_hybrid_fields dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0105_add_hybrid_fields.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0104_ldap_config")' in content, "Missing dependency on 0104"
    assert "hybrid_alpha" in content, "Missing hybrid_alpha field"
    assert "hybrid_enabled" in content, "Missing hybrid_enabled field"

    print("PASS: 0105 migration has correct dependencies")
    return True


def test_0106_migration_dependencies():
    """Test 0106_add_ldap_dn dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0106_add_ldap_dn.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies
    assert '("database", "0105_add_hybrid_fields")' in content, "Missing dependency on 0105"
    assert "ldap_dn" in content, "Missing ldap_dn field"
    assert "khojuser" in content.lower(), "Missing khojuser model reference"

    print("PASS: 0106 migration has correct dependencies")
    return True


def test_0107_migration_dependencies():
    """Test 0107_alter_entry_embeddings dependencies."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    migration_file = os.path.join(migrations_dir, "0107_alter_entry_embeddings.py")
    with open(migration_file, "r") as f:
        content = f.read()

    # Verify dependencies - depends on 0106_add_ldap_dn
    assert '("database", "0106_add_ldap_dn")' in content, "Missing dependency on 0106"
    assert "embeddings" in content, "Missing embeddings field"
    assert "null=True" in content or "blank=True" in content, "Missing null/blank=True"

    print("PASS: 0107 migration has correct dependencies")
    return True


def test_search_model_config_has_hybrid_alpha_in_model():
    """Test SearchModelConfig model has hybrid_alpha field defined."""
    models_file = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "models",
        "__init__.py",
    )

    with open(models_file, "r") as f:
        content = f.read()

    # Verify hybrid_alpha field exists in SearchModelConfig
    assert "hybrid_alpha" in content, "Missing hybrid_alpha field in model"
    assert "SearchModelConfig" in content, "Missing SearchModelConfig class"

    print("PASS: SearchModelConfig has hybrid_alpha field")
    return True


def test_search_model_config_has_hybrid_enabled_in_model():
    """Test SearchModelConfig model has hybrid_enabled field defined."""
    models_file = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "models",
        "__init__.py",
    )

    with open(models_file, "r") as f:
        content = f.read()

    # Verify hybrid_enabled field exists in SearchModelConfig
    assert "hybrid_enabled" in content, "Missing hybrid_enabled field in model"

    print("PASS: SearchModelConfig has hybrid_enabled field")
    return True


def test_khoj_user_has_ldap_dn_in_model():
    """Test KhojUser model has ldap_dn field defined."""
    models_file = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "models",
        "__init__.py",
    )

    with open(models_file, "r") as f:
        content = f.read()

    # Verify ldap_dn field exists in KhojUser
    assert "ldap_dn" in content, "Missing ldap_dn field in model"
    assert "KhojUser" in content, "Missing KhojUser class"

    print("PASS: KhojUser has ldap_dn field")
    return True


def test_entry_model_has_embeddings_field():
    """Test Entry model has embeddings field defined."""
    models_file = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "models",
        "__init__.py",
    )

    with open(models_file, "r") as f:
        content = f.read()

    # Verify embeddings field exists in Entry
    assert "embeddings" in content, "Missing embeddings field in model"
    assert "class Entry" in content, "Missing Entry class"

    print("PASS: Entry has embeddings field")
    return True


def test_entry_save_method_exists():
    """Test Entry model has save method defined."""
    models_file = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "models",
        "__init__.py",
    )

    with open(models_file, "r") as f:
        content = f.read()

    # Verify save method exists in Entry class
    assert "def save" in content, "Missing save method in Entry class"
    # Verify the validation logic exists
    assert "ValidationError" in content or "super().save" in content, "Missing validation or super().save()"

    print("PASS: Entry has save method with validation")
    return True


def test_migration_chain_forms_valid_sequence():
    """Test that migration dependencies form a valid chain."""
    migrations_dir = os.path.join(
        get_project_root(),
        "src",
        "khoj",
        "database",
        "migrations",
    )

    # Read all migration files and extract dependencies
    migration_files = [
        "0100_add_search_vector.py",
        "0101_add_context_summary.py",
        "0102_add_chunk_scale.py",
        "0103_add_ldap_dn_to_user.py",
        "0104_ldap_config.py",
        "0105_add_hybrid_fields.py",
        "0106_add_ldap_dn.py",
        "0107_alter_entry_embeddings.py",
    ]

    dependencies = {}
    for migration_file in migration_files:
        file_path = os.path.join(migrations_dir, migration_file)
        with open(file_path, "r") as f:
            content = f.read()

        # Extract migration name
        migration_name = migration_file.replace(".py", "")

        # Find dependencies
        if '("database", "' in content:
            # Extract dependency
            start = content.find('("database", "') + len('("database", "')
            end = content.find('"', start)
            dep = content[start:end]
            dependencies[migration_name] = dep

    # Verify chain
    expected_chain = [
        ("0100_add_search_vector", "0099_usermemory"),
        ("0101_add_context_summary", "0100_add_search_vector"),
        ("0102_add_chunk_scale", "0101_add_context_summary"),
        ("0103_add_ldap_dn_to_user", "0102_add_chunk_scale"),
        ("0104_ldap_config", "0103_add_ldap_dn_to_user"),
        ("0105_add_hybrid_fields", "0104_ldap_config"),
        ("0106_add_ldap_dn", "0105_add_hybrid_fields"),
        ("0107_alter_entry_embeddings", "0106_add_ldap_dn"),
    ]

    for migration, expected_dep in expected_chain:
        actual_dep = dependencies.get(migration)
        assert actual_dep == expected_dep, f"Migration {migration} should depend on {expected_dep}, got {actual_dep}"

    print("PASS: Migration chain forms valid sequence")
    return True


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_pyproject_toml_syntax_is_valid,
        test_version_is_set_correctly,
        test_required_dependencies_present,
        test_migrations_0100_to_0107_exist,
        test_0100_migration_dependencies,
        test_0101_migration_dependencies,
        test_0102_migration_dependencies,
        test_0103_migration_dependencies,
        test_0104_migration_dependencies,
        test_0105_migration_dependencies,
        test_0106_migration_dependencies,
        test_0107_migration_dependencies,
        test_search_model_config_has_hybrid_alpha_in_model,
        test_search_model_config_has_hybrid_enabled_in_model,
        test_khoj_user_has_ldap_dn_in_model,
        test_entry_model_has_embeddings_field,
        test_entry_save_method_exists,
        test_migration_chain_forms_valid_sequence,
    ]

    passed = 0
    failed = 0
    failures = []

    print("=" * 60)
    print("CRITICAL FIXES TESTS")
    print("=" * 60)
    print()

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append((test.__name__, str(e)))
            print(f"FAIL: {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            failures.append((test.__name__, str(e)))
            print(f"ERROR: {test.__name__}: {e}")

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failures:
        print()
        print("FAILURES:")
        for name, error in failures:
            print(f"  - {name}: {error}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
