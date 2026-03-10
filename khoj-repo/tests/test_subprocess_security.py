"""
Test that verifies no shell=True exists in subprocess calls.
shell=True is a security risk as it can lead to shell injection vulnerabilities.
"""
import os
import re
import pytest
from pathlib import Path

# Get the source directory to scan
SRC_DIR = Path(__file__).parent.parent / "src" / "khoj"


def get_python_files(directory: Path) -> list[Path]:
    """Recursively get all Python files in the directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip test files, __pycache__, and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith("_") and d not in ["tests", "__pycache__"]]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files


def find_subprocess_calls_with_shell(content: str, file_path: str) -> list[dict]:
    """
    Find all subprocess calls that use shell=True or fail to use shell=False.
    Returns list of matches with line numbers and context.
    """
    matches = []
    lines = content.split("\n")
    
    # Regex to find shell=True or shell = True
    shell_true_pattern = re.compile(r'\bshell\s*=\s*True\b', re.IGNORECASE)
    
    # Regex to find subprocess calls (run, Popen, call, check_output, etc.)
    subprocess_pattern = re.compile(
        r'(subprocess\.(run|Popen|call|check_output|check_call|getoutput|getstatusoutput|getstatus)'
        r'|asyncio\.create_subprocess_shell)'
    )
    
    in_subprocess_call = False
    for i, line in enumerate(lines, 1):
        # Check for shell=True
        if shell_true_pattern.search(line):
            matches.append({
                "file": file_path,
                "line": i,
                "content": line.strip(),
                "issue": "shell=True found (security risk)"
            })
    
    return matches


def find_subprocess_calls(content: str, file_path: str) -> list[dict]:
    """
    Find all subprocess calls in the content.
    Returns list of matches with line numbers.
    """
    matches = []
    lines = content.split("\n")
    
    # Patterns for subprocess calls
    subprocess_patterns = [
        r'subprocess\.run\(',
        r'subprocess\.Popen\(',
        r'subprocess\.call\(',
        r'subprocess\.check_output\(',
        r'subprocess\.check_call\(',
        r'subprocess\.getoutput\(',
        r'subprocess\.getstatusoutput\(',
        r'subprocess\.getstatus\(',
        r'asyncio\.create_subprocess_shell\(',
    ]
    
    combined_pattern = re.compile("|".join(subprocess_patterns))
    
    for i, line in enumerate(lines, 1):
        if combined_pattern.search(line):
            matches.append({
                "file": file_path,
                "line": i,
                "content": line.strip()
            })
    
    return matches


# Standalone test functions that don't require Django


def test_no_shell_true_in_subprocess_calls():
    """
    Verify that no subprocess calls use shell=True.
    
    shell=True is a security vulnerability that can lead to shell injection
    attacks. Always use shell=False and pass commands as lists instead.
    """
    violations = []
    
    for py_file in get_python_files(SRC_DIR):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        # Find any shell=True
        shell_true_matches = find_subprocess_calls_with_shell(content, str(py_file))
        violations.extend(shell_true_matches)
    
    if violations:
        error_msg = "\n".join([
            f"  File {v['file']}, line {v['line']}: {v['content']}"
            for v in violations
        ])
        pytest.fail(
            f"Found {len(violations)} shell=True violation(s) in subprocess calls:\n{error_msg}\n\n"
            "shell=True is a security risk. Use shell=False with command as list instead."
        )


def test_subprocess_uses_shell_false_or_no_shell_param():
    """
    Verify that subprocess calls either explicitly use shell=False
    or omit the shell parameter (which defaults to False).
    
    For security, all subprocess calls should use shell=False explicitly
    or be designed to work without shell involvement.
    """
    issues = []
    
    for py_file in get_python_files(SRC_DIR):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        # Find all subprocess calls
        subprocess_calls = find_subprocess_calls(content, str(py_file))
        
        if not subprocess_calls:
            continue
        
        # Check each call for shell parameter
        lines = content.split("\n")
        for call in subprocess_calls:
            line_idx = call["line"] - 1
            if line_idx >= len(lines):
                continue
            
            line = lines[line_idx]
            
            # Check if shell parameter is present
            # Look for shell=True or shell=False in this line or nearby
            # (within 3 lines for multiline calls)
            context = "\n".join(lines[line_idx:min(line_idx + 3, len(lines))])
            
            # If shell= is not explicitly set to False, it could be problematic
            # Note: This is a heuristic check
            has_shell_false = re.search(r'\bshell\s*=\s*False\b', context)
            has_shell_true = re.search(r'\bshell\s*=\s*True\b', context)
            
            if has_shell_true:
                issues.append({
                    "file": call["file"],
                    "line": call["line"],
                    "content": call["content"],
                    "issue": "Uses shell=True"
                })
    
    if issues:
        error_msg = "\n".join([
            f"  File {i['file']}, line {i['line']}: {i['content']}"
            for i in issues
        ])
        pytest.fail(
            f"Found {len(issues)} subprocess call(s) with security issues:\n{error_msg}"
        )


def test_subprocess_calls_in_codebase():
    """
    Report all subprocess calls in the codebase for review.
    This is an informational test that helps track subprocess usage.
    """
    all_calls = []
    
    for py_file in get_python_files(SRC_DIR):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        calls = find_subprocess_calls(content, str(py_file))
        all_calls.extend(calls)
    
    # This test always passes but provides information
    # In a real scenario, you might want to assert on specific counts
    if all_calls:
        print(f"\n\nFound {len(all_calls)} subprocess call(s) in the codebase:")
        for call in all_calls[:10]:  # Show first 10
            print(f"  {call['file']}:{call['line']} - {call['content'][:80]}...")
        if len(all_calls) > 10:
            print(f"  ... and {len(all_calls) - 10} more")
    
    # Verify none use shell=True
    assert len([c for c in all_calls if "shell=True" in c.get("content", "")]) == 0, \
        "Found subprocess calls using shell=True"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
