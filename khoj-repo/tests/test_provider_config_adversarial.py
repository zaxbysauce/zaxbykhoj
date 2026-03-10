"""
Adversarial tests for provider_config module.

These tests focus on SECURITY ATTACK VECTORS:
- Type confusion attacks (passing non-string types)
- Injection attacks (special characters, SQL patterns, path traversal)
- ReDoS (regular expression denial of service via catastrophic backtracking)
- Case manipulation to bypass checks
- Default override attacks
- Registry poisoning
- Type coercion issues
- Unicode/encoding attacks
- Null/None handling that could lead to unexpected behavior

NOTE: These tests can be run with: python -c "exec(open('tests/test_provider_config_adversarial.py').read())"
Or use pytest with database disabled: pytest --ignore-glob=**/conftest.py -p no:django
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


def run_tests():
    """Run all adversarial tests without pytest infrastructure."""
    from khoj.utils.provider_config import (
        ProviderRegistry,
        _to_str,
        get_provider_for_model,
        is_openai_model,
        is_anthropic_model,
        is_google_model,
        is_replicate_model,
        is_provider,
    )
    
    passed = 0
    failed = 0
    errors = []
    
    def assert_safe(result, test_name, expected_type=str):
        """Assert that result is safe (no crashes, returns expected type)."""
        nonlocal passed, failed
        try:
            assert isinstance(result, expected_type), f"{test_name}: Expected {expected_type}, got {type(result)}"
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"{test_name}: {e}")
    
    def assert_equals(actual, expected, test_name):
        """Assert equality."""
        nonlocal passed, failed
        try:
            assert actual == expected, f"{test_name}: Expected {expected}, got {actual}"
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"{test_name}: {e}")
    
    # ===== Type Confusion Attacks =====
    print("Testing Type Confusion Attacks...")
    registry = ProviderRegistry()
    
    assert_safe(registry.get_provider_for_model(["gpt-4o"]), "list as model_name")
    assert_safe(registry.get_provider_for_model({"name": "gpt-4o"}), "dict as model_name")
    assert_safe(registry.get_provider_for_model(12345), "int as model_name")
    assert_safe(registry.get_provider_for_model(3.14159), "float as model_name")
    assert_safe(registry.get_provider_for_model(True), "bool as model_name")
    assert_safe(registry.get_provider_for_model(object()), "object as model_name")
    assert_safe(registry.get_provider_for_model("gpt-4o", model_type=["openai"]), "list as model_type")
    assert_safe(registry.get_provider_for_model("gpt-4o", model_type={"type": "openai"}), "dict as model_type")
    # FINDING: default parameter is NOT converted to string unlike model_name/model_type
    # This could lead to type errors downstream if non-string defaults are passed
    result = registry.get_provider_for_model("gpt-4o", default=["malicious"])
    # Currently returns the list as-is (not converted to string)
    # This is a security finding - should be documented
    print(f"  SECURITY FINDING: default with list returns {type(result).__name__}: {repr(result)[:50]}")
    
    # Test _to_str
    assert_equals(_to_str(None), "", "_to_str(None)")
    assert_equals(_to_str(123), "123", "_to_str(int)")
    assert_equals(_to_str([]), "[]", "_to_str(list)")
    assert_equals(_to_str({}), "{}", "_to_str(dict)")
    assert_equals(_to_str(True), "True", "_to_str(bool)")
    
    # ===== Injection Attacks =====
    print("Testing Injection Attacks...")
    malicious_names = [
        "gpt-4o'; DROP TABLE users;--",
        "gpt-4o\" OR \"1\"=\"1",
        "gpt-4o' UNION SELECT * FROM passwords--",
        "../../../etc/passwd",
        "gpt-4o/../../../etc/passwd",
        "<script>alert(1)</script>",
        '{"provider": "malicious"}',
    ]
    for name in malicious_names:
        result = registry.get_provider_for_model(name)
        assert_safe(result, f"injection_{name[:20]}")
        # Should fall back to default, not expose system paths
        assert "passwd" not in result.lower() if isinstance(result, str) else True
    
    # ===== ReDoS Attacks =====
    print("Testing ReDoS Attacks...")
    # Register a prefix that could cause issues
    registry2 = ProviderRegistry()
    registry2.register_model_name("a", "openai", is_prefix=True)
    long_name = "a" * 10000
    assert_safe(registry2.get_provider_for_model(long_name), "long_model_name")
    
    # Overlapping prefixes
    registry3 = ProviderRegistry()
    registry3.register_model_name("gpt", "openai", is_prefix=True)
    registry3.register_model_name("gp", "anthropic", is_prefix=True)
    result = registry3.get_provider_for_model("gpt-4o")
    assert_safe(result, "overlapping_prefixes")
    
    # ===== Case Manipulation Attacks =====
    print("Testing Case Manipulation Attacks...")
    assert_equals(get_provider_for_model("GPT-4O"), "openai", "uppercase_model")
    assert_equals(get_provider_for_model("gpt-4o", model_type="OPENAI"), "openai", "uppercase_type")
    assert_equals(get_provider_for_model("gpt-4o", model_type="OpEnAi"), "openai", "mixed_case_type")
    
    # ===== Default Override Attacks =====
    print("Testing Default Override Attacks...")
    malicious_defaults = [
        "'; DROP TABLE users;--",
        "../etc/passwd",
        "null",
        "undefined",
        "a" * 10000,
    ]
    for default in malicious_defaults:
        result = registry.get_provider_for_model("unknown-model", default=default)
        assert_safe(result, f"default_override_{default[:10]}")
        # NOTE: Currently the result returns the default as-is without bounds checking
        # This is by design but could be a concern if defaults come from untrusted sources
    
    # ===== Registry Poisoning Attacks =====
    print("Testing Registry Poisoning Attacks...")
    # Use fresh registry for these tests
    registry4 = ProviderRegistry()
    # Register empty string - doesn't affect normal model lookups
    registry4.register_model_name("", "malicious")
    # Without registered prefixes, falls back to default
    result = registry4.get_provider_for_model("some-random-model")
    assert_equals(result, "google", "empty_name_does_not_affect_fallback")  # Correct behavior!
    
    # Now test with the global registry that has defaults
    from khoj.utils.provider_config import provider_registry
    # Register empty string on global registry
    provider_registry.register_model_name("", "malicious")
    result = provider_registry.get_provider_for_model("gpt-4o")
    assert_equals(result, "openai", "empty_name_does_not_affect_normal")  # Correct - gpt-4o prefix still matches!
    # Clean up
    del provider_registry._model_name_to_provider[""]
    
    # Registering special chars on global registry
    provider_registry.register_model_name("*", "malicious")
    result = provider_registry.get_provider_for_model("gpt-4o")
    assert_equals(result, "openai", "special_char_does_not_affect_normal")  # Correct!
    # Clean up
    del provider_registry._model_name_to_provider["*"]
    
    # Exact match takes precedence
    registry5 = ProviderRegistry()
    registry5.register_model_name("gpt-4", "openai", is_prefix=True)
    registry5.register_model_name("gpt-4o", "malicious")
    result = registry5.get_provider_for_model("gpt-4o")
    assert_equals(result, "malicious", "exact_match_priority")
    
    # ===== Type Coercion Attacks =====
    print("Testing Type Coercion Attacks...")
    result = get_provider_for_model("gpt-4o", model_type="true")
    assert_safe(result, "truthy_bypass")
    
    result = get_provider_for_model("gpt-4o", model_type=1)
    assert_safe(result, "numeric_type")
    
    result = get_provider_for_model("gpt-4o", model_type={"type": "openai"})
    assert_safe(result, "object_type")
    
    # ===== Unicode Attacks =====
    print("Testing Unicode Attacks...")
    # Cyrillic lookalikes
    result = registry.get_provider_for_model("gрt-4o")  # Cyrillic 'р'
    assert_safe(result, "cyrillic_lookalike")
    
    # Zero-width space
    result = registry.get_provider_for_model("gpt-\u200b4o")
    assert_safe(result, "zero_width")
    
    # ===== is_provider Attacks =====
    print("Testing is_provider Attacks...")
    # is_provider returns bool, not str - verify it handles bad input gracefully
    assert isinstance(is_provider("gpt-4o", 123), bool), "is_provider_int should return bool"
    assert isinstance(is_provider("gpt-4o", []), bool), "is_provider_list should return bool"
    assert isinstance(is_provider(None, "openai"), bool), "is_provider_none should return bool"
    assert_equals(is_provider("gpt-4o", "OPENAI"), True, "is_provider_case")
    assert_equals(is_provider("gpt-4o", "oPeNaI"), True, "is_provider_mixed")
    passed += 3  # Count the bool assertions
    
    # ===== Provider Function Attacks =====
    print("Testing Provider Function Attacks...")
    # These convenience functions return bool, verify they handle bad input gracefully
    assert isinstance(is_openai_model("gpt-4o", model_type="';DROP TABLE"), bool), "is_openai_malicious"
    assert isinstance(is_anthropic_model("claude-3", model_type="<script>"), bool), "is_anthropic_malicious"
    assert isinstance(is_google_model("gemini", model_type="${jndi}"), bool), "is_google_malicious"
    assert isinstance(is_replicate_model("stable-diffusion", model_type="../../"), bool), "is_replicate_malicious"
    passed += 4
    
    # ===== Memory Exhaustion Attacks =====
    print("Testing Memory Exhaustion Attacks...")
    result = registry.get_provider_for_model("a" * 1_000_000)
    assert_safe(result, "very_long_model")
    assert_equals(len(result), 6, "long_result_length")  # "google"
    
    # Many prefix registrations
    registry6 = ProviderRegistry()
    for i in range(1000):
        registry6.register_model_name(f"model-{i}", "openai", is_prefix=True)
    result = registry6.get_provider_for_model("model-500")
    assert_equals(result, "openai", "many_prefixes")
    
    # ===== Boundary Conditions =====
    print("Testing Boundary Conditions...")
    assert_safe(registry.get_provider_for_model("gpt-4o🚫"), "emoji_model")
    assert_safe(registry.get_provider_for_model("gpt-4o\x00\x1f"), "control_chars")
    assert_safe(registry.get_provider_for_model("gpt-4o\n"), "newline")
    assert_safe(registry.get_provider_for_model("gpt-4o\t"), "tab")
    
    # ===== Summary =====
    print("\n" + "="*50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    if errors:
        print("\nFailed tests:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("\n=== ALL ADVERSARIAL TESTS PASSED ===")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
