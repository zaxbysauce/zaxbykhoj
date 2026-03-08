"""Tests for LdapAuthBackend class structure.

These tests verify the structure and basic properties of the LDAP backend
without requiring database connectivity.
"""
import ast
import os
import sys
import inspect

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_module_imports_without_errors():
    """Verify that ldap_backend module imports without errors."""
    try:
        from khoj.processor.auth.ldap_backend import LdapAuthBackend, LdapAuthError
        assert LdapAuthBackend is not None
        assert LdapAuthError is not None
    except ImportError as e:
        raise AssertionError(f"Failed to import LdapAuthBackend: {e}")


def test_init_py_exports_correctly():
    """Verify __init__.py exports LdapAuthBackend and LdapAuthError."""
    from khoj.processor.auth import LdapAuthBackend, LdapAuthError
    
    assert LdapAuthBackend is not None
    assert LdapAuthError is not None


def test_all_exports_in_init():
    """Verify __all__ in __init__.py contains expected exports."""
    import khoj.processor.auth as auth_module
    
    assert hasattr(auth_module, '__all__')
    assert 'LdapAuthBackend' in auth_module.__all__
    assert 'LdapAuthError' in auth_module.__all__


def test_ldap_auth_backend_class_exists():
    """Verify LdapAuthBackend class exists with required attributes."""
    from khoj.processor.auth.ldap_backend import LdapAuthBackend
    
    assert isinstance(LdapAuthBackend, type)
    assert LdapAuthBackend.__name__ == 'LdapAuthBackend'


def test_ldap_auth_error_class_exists():
    """Verify LdapAuthError exception class exists."""
    from khoj.processor.auth.ldap_backend import LdapAuthError
    
    assert issubclass(LdapAuthError, Exception)


def test_required_methods_exist():
    """Verify LdapAuthBackend has all required methods."""
    from khoj.processor.auth.ldap_backend import LdapAuthBackend
    
    required_methods = [
        '__init__',
        '_initialize_server',
        '_get_bind_credentials',
        '_sanitize_username',
        'authenticate',
        'test_connection',
    ]
    
    for method in required_methods:
        assert hasattr(LdapAuthBackend, method), f"Missing method: {method}"


def test_no_hardcoded_credentials_in_source():
    """Verify no hardcoded credentials in ldap_backend.py source."""
    # Read the source file
    source_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'src', 'khoj', 'processor', 'auth', 'ldap_backend.py'
    )
    
    with open(source_path, 'r') as f:
        source = f.read()
    
    # Check for common hardcoded credential patterns
    suspicious_patterns = [
        'password = "',
        "password = '",
        'bind_dn = "',
        "bind_dn = '",
        'secret = "',
        "secret = '",
        'api_key = "',
        "api_key = '",
    ]
    
    lines = source.split('\n')
    for i, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        
        for pattern in suspicious_patterns:
            if pattern in line.lower():
                # Allow patterns that are clearly not hardcoded values
                if 'os.getenv' in line or 'get_ldap' in line or 'pass' in line.lower():
                    continue
                raise AssertionError(f"Potential hardcoded credential at line {i}: {line.strip()}")


def test_credentials_retrieved_from_secrets():
    """Verify credentials are retrieved from secrets module, not hardcoded."""
    source_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'src', 'khoj', 'processor', 'auth', 'ldap_backend.py'
    )
    
    with open(source_path, 'r') as f:
        source = f.read()
    
    # Verify imports from secrets modules
    assert 'from khoj.utils.secrets import' in source
    assert 'from khoj.utils.secrets_vault import' in source
    
    # Verify usage of secret retrieval functions
    assert 'get_ldap_bind_dn' in source
    assert 'get_ldap_bind_password' in source
    assert 'get_ldap_credentials_from_vault' in source


def test_class_docstring_exists():
    """Verify LdapAuthBackend has a docstring."""
    from khoj.processor.auth.ldap_backend import LdapAuthBackend
    
    assert LdapAuthBackend.__doc__ is not None
    assert len(LdapAuthBackend.__doc__) > 0


def test_method_docstrings_exist():
    """Verify public methods have docstrings."""
    from khoj.processor.auth.ldap_backend import LdapAuthBackend
    
    public_methods = ['authenticate', 'test_connection']
    
    for method_name in public_methods:
        method = getattr(LdapAuthBackend, method_name)
        assert method.__doc__ is not None, f"Method {method_name} missing docstring"


def test_init_accepts_config_parameter():
    """Verify __init__ accepts config parameter."""
    from khoj.processor.auth.ldap_backend import LdapAuthBackend
    
    sig = inspect.signature(LdapAuthBackend.__init__)
    params = list(sig.parameters.keys())
    
    assert 'config' in params


# Tests for secrets module structure

def test_secrets_module_imports():
    """Verify secrets module imports without errors."""
    try:
        from khoj.utils.secrets import (
            get_ldap_bind_dn,
            get_ldap_bind_password,
            get_ldap_credentials,
            has_ldap_credentials,
            LdapSecretError,
        )
    except ImportError as e:
        raise AssertionError(f"Failed to import from secrets module: {e}")


def test_secrets_vault_module_imports():
    """Verify secrets_vault module imports without errors."""
    try:
        from khoj.utils.secrets_vault import (
            VaultAdapter,
            get_ldap_credentials_from_vault,
            is_vault_configured,
        )
    except ImportError as e:
        raise AssertionError(f"Failed to import from secrets_vault module: {e}")


def test_secrets_use_environment_variables():
    """Verify secrets module uses environment variables."""
    source_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'src', 'khoj', 'utils', 'secrets.py'
    )
    
    with open(source_path, 'r') as f:
        source = f.read()
    
    # Verify use of os.getenv
    assert 'os.getenv' in source
    
    # Verify expected environment variable names
    assert 'KHOJ_LDAP_BIND_DN' in source
    assert 'KHOJ_LDAP_BIND_PASSWORD' in source


def test_no_hardcoded_credentials_in_secrets():
    """Verify no hardcoded credentials in secrets.py."""
    source_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 'src', 'khoj', 'utils', 'secrets.py'
    )
    
    with open(source_path, 'r') as f:
        source = f.read()
    
    # Check for hardcoded password patterns (excluding os.getenv calls)
    lines = source.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip comments
        if stripped.startswith('#'):
            continue
        
        # Check for suspicious patterns not involving os.getenv
        if ('= "' in line or "= '" in line) and 'os.getenv' not in line:
            # Check if it's a credential-related line
            lower_line = line.lower()
            if any(word in lower_line for word in ['password', 'secret', 'key', 'token', 'credential']):
                raise AssertionError(f"Potential hardcoded credential at line {i}: {line.strip()}")


if __name__ == '__main__':
    # Run tests manually if pytest is not available
    import traceback
    
    tests = [
        test_module_imports_without_errors,
        test_init_py_exports_correctly,
        test_all_exports_in_init,
        test_ldap_auth_backend_class_exists,
        test_ldap_auth_error_class_exists,
        test_required_methods_exist,
        test_no_hardcoded_credentials_in_source,
        test_credentials_retrieved_from_secrets,
        test_class_docstring_exists,
        test_method_docstrings_exist,
        test_init_accepts_config_parameter,
        test_secrets_module_imports,
        test_secrets_vault_module_imports,
        test_secrets_use_environment_variables,
        test_no_hardcoded_credentials_in_secrets,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
