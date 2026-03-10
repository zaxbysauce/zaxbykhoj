# Khoj Codebase Analysis - Category 3: Cross-Platform & Environment Issues

## Overview
Analysis of Python and TypeScript files in the Khoj codebase for cross-platform compatibility issues. Scope: All source files in `khoj-repo/src/khoj` (Python) and `khoj-repo/src/interface` (TypeScript). Excluded: test files, node_modules, .git, dist, __pycache__, .venv.

---

## CRITICAL Issues

### 1. Hardcoded Unix Home Directory
**File:** `khoj-repo/src/khoj/processor/tools/run_code.py`
**Line:** 45
**Severity:** CRITICAL

**Problem:**
```python
HOME_DIR = "/home/user"
```
The code hardcodes a Unix home directory path, which will fail on Windows systems (where home directories use `C:\Users\username`).

**Impact:**
- Will cause file system operations to fail on Windows
- Breaks the E2B sandbox file operations which rely on this path

**Suggested Fix:**
```python
import os

HOME_DIR = os.getenv("E2B_HOME_DIR", "/home/user")
```

---

### 2. Hardcoded Unix Shell Commands
**File:** `khoj-repo/src/khoj/processor/operator/operator_environment_computer.py`
**Lines:** 364, 369, 433, 460
**Severity:** CRITICAL

**Problem:**
The file uses multiple Unix-specific shell commands:
```python
# Line 364
cmd = rf"find {escaped_path} -maxdepth 2 -not -path '*/\.*'"

# Line 369
cmd = f"head -n {end_line} '{escaped_path}' | tail -n {lines_to_show}"

# Line 433
cmd = f"sed -i.bak 's/{escaped_old}/{escaped_new}/g' '{escaped_path}'"

# Line 460
cmd = f"sed -i.bak '{insert_line}a\\{escaped_content}' '{escaped_path}'"
```

**Impact:**
- Fails completely on Windows (no `find`, `head`, `tail`, or `sed -i`)
- Requires WSL or similar Unix layer on Windows
- Any path operations will fail with non-Unix filesystems

**Suggested Fix:**
Implement platform-independent Python solutions:
```python
# Replace find with os.scandir() or pathlib.Path.glob()
cmd = rf"{' '.join(str(f) for f in Path(escaped_path).glob('*'))}"

# Replace head/tail with slicing
with open(escaped_path, 'r') as f:
    lines = f.readlines()
    output = ''.join(lines[start_line:end_line])

# Replace sed with Python string replacement
with open(escaped_path, 'r') as f:
    content = f.read()
    content = content.replace(old_str, new_str)
with open(escaped_path, 'w') as f:
    f.write(content)
```

---

### 3. Hardcoded Unix Tilde Paths
**Files:**
- `khoj-repo/src/khoj/utils/cli.py` (Line 13)
- `khoj-repo/src/khoj/utils/constants.py` (Lines 11, 13, 20, 27)

**Severity:** CRITICAL

**Problem:**
```python
# cli.py line 13
default="~/.khoj/khoj.log",

# constants.py lines 11, 13, 20, 27
app_env_filepath = "~/.khoj/env"
content_directory = "~/.khoj/content/"
"model_directory": "~/.khoj/search/image/"
```

**Impact:**
- Tilde expansion (`~`) works differently on different platforms
- Windows: Requires manual conversion or `Path.home()`
- Cross-platform path building will fail without proper expansion

**Suggested Fix:**
```python
import pathlib

# Replace with pathlib.Path.home()
default=Path.home() / ".khoj" / "khoj.log",
app_env_filepath = Path.home() / ".khoj" / "env"
content_directory = Path.home() / ".khoj" / "content"
model_directory = Path.home() / ".khoj" / "search" / "image"
```

---

### 4. Hardcoded Unix Socket Path
**File:** `khoj-repo/src/khoj/utils/cli.py`
**Line:** 23
**Severity:** CRITICAL

**Problem:**
```python
help="Path to UNIX socket for server. Use to run server behind reverse proxy. Default: /tmp/uvicorn.sock",
```

**Impact:**
- Unix socket paths only work on Unix-like systems
- Fails on Windows where Unix sockets are not supported
- Users on Windows cannot use the socket-based configuration

**Suggested Fix:**
```python
help="Path to socket file for server. Unix sockets only work on Unix-like systems. Default: None (use TCP)."
```

Or provide a TCP port fallback for Windows:
```python
# Detect platform
import platform
is_unix = platform.system() not in ['Windows', 'CYGWIN', 'MSYS']

if is_unix:
    parser.add_argument(
        "--socket",
        type=pathlib.Path,
        help="Path to UNIX socket for server (Unix-only)."
    )
else:
    parser.add_argument(
        "--port",
        type=int,
        default=42110,
        help="TCP port for server (Windows)."
    )
```

---

### 5. Hardcoded Path Separators in URL/API Parsing
**File:** `khoj-repo/src/khoj/utils/helpers.py`
**Lines:** 389, 885, 1116

**Severity:** MAJOR

**Problem:**
```python
# Line 389 - Parsing $ref paths
def_name = ref_path.split("/")[-1]

# Line 885 - Parsing image data URI
image_type = image_data_uri.split(";")[0].split(":")[1].split("/")[1]

# Line 1116 - Parsing API URL path
path_parts = parsed_api_url.path.split("/")
```

**Impact:**
- Path separator assumptions break on Windows (`\` vs `/`)
- URL path parsing will fail with Windows file paths
- Any URL-like strings containing backslashes will break

**Suggested Fix:**
```python
# Use pathlib.Path for all path operations
from pathlib import Path

# Line 389
if ref_path.startswith("#/$defs/"):
    def_name = Path(ref_path.replace("#/$defs/", "")).name

# Line 885
image_parts = image_data_uri.split(";")[0].split(":")[1].split("/")
image_type = image_parts[-1]  # Last part is the type

# Line 1116
path_parts = [p for p in parsed_api_url.path.split("/") if p]
```

---

## MAJOR Issues

### 6. Shell=True in Subprocess Calls
**File:** `khoj-repo/src/khoj/processor/operator/operator_environment_computer.py`
**Lines:** 522, 637
**Severity:** MAJOR

**Problem:**
```python
# Line 522 (local execution)
process = await asyncio.to_thread(
    subprocess.run,
    command,
    shell=True,  # <-- Shell interpretation
    ...
)

# Line 637 (Docker execution)
process = await asyncio.to_thread(
    subprocess.run,
    docker_full_cmd,
    shell=True,  # <-- Shell interpretation
    ...
)
```

**Impact:**
- Shell interpretation is platform-specific
- Requires escaping handling varies by platform
- Security risk: shell injection vulnerabilities
- More complex error handling needed

**Suggested Fix:**
Use list-of-strings for subprocess calls instead of shell=True:
```python
# Convert shell commands to proper argument lists
if self.provider == "docker":
    docker_args = [
        "docker", "exec",
        "-e", f"DISPLAY={self.docker_display}",
        self.docker_container_name,
        "bash", "-c", command
    ]
else:
    args = command.split()
    process = await asyncio.to_thread(
        subprocess.run,
        args,
        capture_output=True,
        ...
    )
```

---

### 7. Environment OS Mapping
**File:** `khoj-repo/src/khoj/processor/operator/operator_agent_openai.py`
**Lines:** 404-405
**Severity:** MAJOR

**Problem:**
```python
# Line 404-405
environment_os = "linux"
# environment = "mac" if platform.system() == "Darwin" else "windows" if platform.system() == "Windows" else "linux"
```

**Impact:**
- Hardcoded "linux" instead of detecting actual platform
- May cause environment-specific issues on Windows/Mac
- Requires manual update when changing environments

**Suggested Fix:**
```python
import platform

environment_os = platform.system().lower()
if environment_os == "darwin":
    environment_os = "mac"
elif environment_os == "windows":
    environment_os = "windows"
```

---

### 8. Unix Tool Dependencies in Documentation
**File:** `khoj-repo/src/khoj/utils/cli.py`
**Line:** 23
**Severity:** MAJOR

**Problem:**
```python
help="Path to UNIX socket for server. Use to run server behind reverse proxy. Default: /tmp/uvicorn.sock",
```

**Impact:**
- Misleading for Windows users
- No mention of Windows limitations or alternatives
- May cause confusion when configuration fails on Windows

**Suggested Fix:**
```python
help="Path to Unix socket for server (Unix-like systems only). "
     "For Windows, use TCP port instead. "
     "Default: None (use TCP port)"
```

---

## MINOR Issues

### 9. Path Parsing Without Normalization
**File:** `khoj-repo/src/khoj/utils/secrets_vault.py`
**Lines:** 77-78
**Severity:** MINOR

**Problem:**
```python
# Line 77-78
mount_point = path.split("/")[0]
secret_path = "/".join(path.split("/")[1:])
```

**Impact:**
- Only works with forward slash separators
- Fails with Windows paths containing backslashes
- Path components may be incorrectly parsed on case-insensitive filesystems

**Suggested Fix:**
```python
from pathlib import Path

path_obj = Path(path)
mount_point = str(path_obj.parts[0])
secret_path = "/".join(path_obj.parts[1:]) if len(path_obj.parts) > 1 else ""
```

---

### 10. Environment Variable Documentation
**File:** `khoj-repo/src/khoj/processor/tools/run_code.py`
**Line:** 44
**Severity:** MINOR

**Problem:**
```python
DEFAULT_E2B_TEMPLATE = "pmt2o0ghpang8gbiys57"
```

**Impact:**
- No documentation of this hardcoded value
- Not clear if this is platform-specific or universal
- Difficult to maintain without clear purpose

**Suggested Fix:**
```python
DEFAULT_E2B_TEMPLATE = "pmt2o0ghpang8gbiys57"  # Default E2B template ID
# Document that this is a template ID, not a path
```

Or add a comment:
```python
DEFAULT_E2B_TEMPLATE = "pmt2o0ghpang8gbiys57"  # Default E2B template - works across all platforms
```

---

## Positive Findings

### Good Practices Found:
1. **Proper Encoding**: Most file operations use `encoding="utf-8"` (e.g., `jsonl.py`)
2. **Pathlib Usage**: Extensive use of `pathlib.Path` throughout the codebase
3. **Platform Detection**: `platform.system()` used in a few places
4. **Environment Variables**: Uses `os.getenv()` for configurable values

---

## Summary Statistics

- **CRITICAL Issues:** 4
- **MAJOR Issues:** 3
- **MINOR Issues:** 2
- **Total Issues:** 9

---

## Recommendations

1. **Priority 1 (Immediate):** Fix hardcoded Unix home directory and path separators
2. **Priority 2 (High):** Replace Unix shell commands with Python-native solutions
3. **Priority 3 (Medium):** Normalize all path handling to use `pathlib.Path`
4. **Priority 4 (Low):** Update documentation to clarify platform limitations
5. **Consider:** Add CI/CD tests for cross-platform compatibility

---

## Cross-Platform Testing Recommendations

1. Test on Windows (Native and WSL)
2. Test on macOS (Intel and M1/M2)
3. Test on Linux (various distributions)
4. Test on network-mounted filesystems
5. Test case-sensitive vs case-insensitive filesystems
