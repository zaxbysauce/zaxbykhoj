# Security Analysis - Category 2: Security & Data Handling

**Analysis Date:** March 8, 2026
**Scope:** All Python and TypeScript files in main codebase
**Excluded:** node_modules/, .git/, dist/, __pycache__/, .venv/

---

## CRITICAL SEVERITY FINDINGS

### 1. Hardcoded Credentials in Docker Compose Configuration
**File:** `khoj-repo/docker-compose.yml`
**Line:** 71-74

**Problem:**
```yaml
- KHOJ_DJANGO_SECRET_KEY=secret
- KHOJ_ADMIN_EMAIL=username@example.com
- KHOJ_ADMIN_PASSWORD=password
```
The Django secret key and admin password are hardcoded as example values in the docker-compose.yml file. This is a production-ready file that should not contain such values.

**Impact:**
- Allows any attacker to authenticate as admin if they can access these credentials
- Weak Django secret key compromises session security and cryptographic signing
- Insecure default configuration that could be used by malicious actors

**Fix:**
```yaml
# Remove these lines or require user to set via environment variables
# KHOJ_DJANGO_SECRET_KEY should be a cryptographically secure random string
# KHOJ_ADMIN_PASSWORD should be set separately and never committed to version control
- KHOJ_DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
- KHOJ_ADMIN_EMAIL=${DJANGO_ADMIN_EMAIL}
- KHOJ_ADMIN_PASSWORD=${DJANGO_ADMIN_PASSWORD}
```

---

## MAJOR SEVERITY FINDINGS

### 2. Unsafe eval() Usage in Image Grounding Agent
**File:** `khoj-repo/src/khoj/processor/operator/grounding_agent_uitars.py`
**Lines:** 682, 685, 695, 720, 879, 882, 891, 918

**Problem:**
Multiple uses of `eval()` function to parse box coordinates from user-supplied action inputs:
```python
x1, y1, x2, y2 = eval(start_box)  # Line 682, 695, 879, 891
x1, y1, x2, y2 = eval(end_box)    # Line 685, 882
start_box = eval(start_box)       # Line 720, 918
```

**Impact:**
- Direct execution of arbitrary Python code from user input
- Potential for code injection attacks if the grounding agent accepts malicious inputs
- The eval() calls are used to parse coordinate boxes, but no validation is performed

**Fix:**
```python
def parse_box_coordinates(box_str: str) -> Tuple[float, float, float, float]:
    """Parse box coordinates with strict validation."""
    try:
        # Use ast.literal_eval instead of eval for safe parsing
        coords = ast.literal_eval(box_str)
        if not isinstance(coords, (list, tuple)) or len(coords) != 4:
            raise ValueError("Box coordinates must be a tuple/list of 4 numbers")
        if not all(isinstance(c, (int, float)) for c in coords):
            raise ValueError("Box coordinates must be numeric")
        return tuple(float(c) for c in coords)
    except (ValueError, SyntaxError) as e:
        raise ValueError(f"Invalid box format: {e}")

# Replace all eval() calls with parse_box_coordinates()
x1, y1, x2, y2 = parse_box_coordinates(start_box)
```

**Alternative Fix (if string format is required):**
```python
import ast

# Validate the string format before eval
if not re.match(r'^\[\d+\.?\d*,\s*\d+\.?\d*,\s*\d+\.?\d*,\s*\d+\.?\d*\]$', box_str):
    raise ValueError("Box coordinates must be in format [x1, y1, x2, y2]")

x1, y1, x2, y2 = ast.literal_eval(box_str)
```

---

### 3. Pickle Deserialization in Migration File
**File:** `khoj-repo/src/khoj/database/migrations/0064_remove_conversation_temp_id_alter_conversation_id.py`
**Lines:** 25, 40

**Problem:**
The migration file uses pickle to serialize/deserialize Django job state:
```python
job_state = pickle.loads(job.job_state)
# ...
job.job_state = pickle.dumps(job_state)
```

**Impact:**
- Pickle deserialization is vulnerable to remote code execution attacks
- If an attacker can control the job_state data in the database, they can execute arbitrary Python code
- While migrations run with elevated privileges, this is a potential security risk

**Fix:**
```python
import json

# Use JSON instead of pickle for serialization
def safe_json_serializer(obj):
    """Handle JSON serialization for complex objects."""
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Type {type(obj)} not serializable")

# Replace pickle with JSON
try:
    job_state = json.loads(job.job_state)
except json.JSONDecodeError:
    # Handle legacy pickle format during migration
    job_state = json.loads(pickle.loads(job.job_state))
    # Update to new JSON format
    job.job_state = json.dumps(job_state, default=safe_json_serializer)
    job.save()
    continue
```

**Note:** This is a migration file, so it's unlikely to be exploited in production, but it's still best practice to avoid pickle for sensitive data.

---

### 4. Potential Command Injection via Docker Execution
**File:** `khoj-repo/src/khoj/processor/operator/operator_environment_computer.py`
**Lines:** 626-648

**Problem:**
The code constructs and executes shell commands with user-supplied parameters:
```python
safe_python_cmd = python_command_str.replace('"', '\\"')
docker_full_cmd = (
    f'docker exec -e DISPLAY={self.docker_display} "{self.docker_container_name}" '
    f'python3 -c "{safe_python_cmd}"'
)
```

While the code uses `.replace('"', '\\"')` to escape quotes, this approach has limitations:
- Only escapes quotes, not other shell metacharacters
- If `python_command_str` contains other shell special characters, they could be exploited
- The use of `shell=True` in subprocess.run makes it vulnerable to shell injection

**Impact:**
- If an attacker can control the `python_command_str` parameter, they could execute arbitrary shell commands
- Potentially allows escape from the sandbox environment

**Fix:**
```python
# Use subprocess without shell=True and validate input
async def docker_execute(self, python_command_str: str) -> Optional[str]:
    if not self.docker_container_name or not self.docker_display:
        logger.error("Container name or Docker display not set for Docker execution.")
        return None

    # Validate and sanitize input
    if not re.match(r'^[a-zA-Z0-9_\-\.+=\s]*$', python_command_str):
        raise ValueError("Invalid characters in Python command")

    # Use list of arguments instead of shell string
    docker_full_cmd = [
        'docker', 'exec', '-e', f'DISPLAY={self.docker_display}',
        self.docker_container_name, 'python3', '-c', python_command_str
    ]

    try:
        process = await asyncio.to_thread(
            subprocess.run,
            docker_full_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        # ... rest of error handling
```

---

## MINOR SEVERITY FINDINGS

### 5. Content Security Policy Allows 'unsafe-eval' and 'unsafe-inline'
**File:** `khoj-repo/src/interface/web/app/common/layoutHelper.tsx`
**Lines:** 5-14

**Problem:**
The CSP configuration allows 'unsafe-eval' and 'unsafe-inline':
```typescript
script-src 'self' https://assets.khoj.dev https://app.chatwoot.com https://accounts.google.com 'unsafe-inline' 'unsafe-eval';
```

**Impact:**
- Weakens XSS protection
- Allows JavaScript execution that bypasses some CSP protections
- Could be exploited by XSS vulnerabilities in third-party scripts

**Fix:**
```typescript
export function ContentSecurityPolicy() {
    // Remove 'unsafe-inline' and 'unsafe-eval' where possible
    // Implement nonce-based CSP if dynamic script loading is required
    return (
        <meta
            httpEquiv="Content-Security-Policy"
            content="default-src 'self';
               media-src * blob:;
               script-src 'self' https://assets.khoj.dev https://app.chatwoot.com https://accounts.google.com;
               connect-src 'self' blob: https://ipapi.co/json ws://localhost:42110 https://accounts.google.com;
               style-src 'self' https://assets.khoj.dev 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com;
               img-src 'self' data: blob: https://*.khoj.dev https://accounts.google.com https://*.googleusercontent.com https://*.google.com/ https://*.gstatic.com;
               font-src 'self' https://assets.khoj.dev https://fonts.gstatic.com;
               frame-src 'self' https://accounts.google.com https://app.chatwoot.com;
               child-src 'self' https://app.chatwoot.com;
               object-src none;"
        ></meta>
    );
}
```

---

### 6. Input Validation in File Operations
**File:** `khoj-repo/src/khoj/routers/api_content.py`
**Lines:** 52-68

**Problem:**
File paths are taken directly from user input without sanitization:
```python
class File(BaseModel):
    path: str
    content: Union[str, bytes]

class IndexBatchRequest(BaseModel):
    files: list[File]
```

**Impact:**
- Potential for path traversal attacks
- Files could be read from unintended locations
- No validation of file names, extensions, or content types

**Fix:**
```python
import os
from pathlib import Path
import mimetypes

class File(BaseModel):
    path: str
    content: Union[str, bytes]

    @validator('path')
    def validate_path(cls, v):
        # Reject absolute paths to prevent directory traversal
        if os.path.isabs(v):
            raise ValueError("Absolute paths are not allowed")
        # Replace path separators to prevent traversal
        safe_path = v.replace('/', os.sep).replace('\\', os.sep)
        # Reject dangerous characters
        if any(c in safe_path for c in ['..', '~', ':', '*']):
            raise ValueError("Invalid characters in path")
        # Validate extension if it's a file
        ext = Path(safe_path).suffix.lower()
        if ext in ['.py', '.sh', '.bash', '.ps1', '.bat', '.cmd']:
            raise ValueError(f"Script files with extension {ext} are not allowed")
        return safe_path

    @validator('content')
    def validate_content(cls, v, values):
        path = values.get('path', '')
        ext = Path(path).suffix.lower()

        # Validate file types and content
        if ext == '.txt':
            if isinstance(v, bytes):
                # Decode and validate
                v = v.decode('utf-8', errors='strict')
                # Check for potentially dangerous patterns
                if any(pattern in v for pattern in ['import os', 'import subprocess', 'os.system']):
                    raise ValueError("Potentially dangerous content detected")
        return v
```

---

### 7. Logging May Leak Sensitive Data
**File:** `khoj-repo/src/khoj/routers/api_content.py`
**Lines:** 597

**Problem:**
Error messages may include potentially sensitive data:
```python
logger.error(f"Failed to {method} {t} data sent by {client} client into content index: {e}", exc_info=True)
```

While the implementation appears safe, there are other logging statements that might leak sensitive data in edge cases.

**Impact:**
- Error logs could contain user data, API keys, or other sensitive information
- Could be exposed in logs or error tracking systems

**Fix:**
```python
# Replace with sanitized logging
logger.error(
    f"Failed to {method} content for user {user.email if hasattr(user, 'email') else 'unknown'}",
    exc_info=True,
    extra={
        'user_id': user.id if hasattr(user, 'id') else None,
        'sanitized_method': method,
        # Don't log the sensitive data or exception directly
    }
)

# Add sensitive data filtering
import re
import logging

SENSITIVE_PATTERNS = [
    r'api[_-]?key\s*[:=]\s*[A-Za-z0-9_-]+',
    r'token\s*[:=]\s*[A-Za-z0-9_-]+',
    r'password\s*[:=]\s*[^\s\n]+',
    r'credentials\s*[:=]\s*\{[^}]*\}',
]

def sanitize_log_message(message: str) -> str:
    """Remove sensitive information from log messages."""
    for pattern in SENSITIVE_PATTERNS:
        message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
    return message

logger.error(sanitize_log_message(f"Failed to {method} data: {e}"), exc_info=True)
```

---

### 8. SQL Injection Risk (Low)
**File:** `khoj-repo/src/khoj/app/settings.py`
**Line:** 154

**Problem:**
Direct SQL query with string formatting:
```python
db_exists_result = PGSERVER_INSTANCE.psql(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
```

**Impact:**
- Potential SQL injection if DB_NAME comes from untrusted input
- While DB_NAME appears to be an internal variable, this is still a risk

**Fix:**
```python
# Use parameterized queries
db_exists_result = PGSERVER_INSTANCE.psql(
    "SELECT 1 FROM pg_database WHERE datname = %s;",
    (DB_NAME,)
)
```

---

### 9. Insufficient Randomness for Security
**Finding:**
The codebase uses Python's `random` module for non-cryptographic purposes, which is acceptable. However, I did not find evidence of using `Math.random()` in security-sensitive contexts in TypeScript code.

**Impact:**
- Minimal security impact as random is not used for cryptographic purposes
- But should be reviewed if any security-sensitive tokens or secrets are generated

**Fix:**
For any security-sensitive operations (tokens, session IDs, encryption keys), use:
- Python: `secrets` module or `os.urandom()`
- TypeScript: Node.js `crypto.randomBytes()` or `crypto.randomUUID()`

---

### 10. Missing Input Validation in Webhook Handlers
**File:** `khoj-repo/src/khoj/routers/email.py`, `khoj-repo/src/khoj/routers/twilio.py`, `khoj-repo/src/khoj/routers/notion.py`

**Problem:**
Webhook handlers receive untrusted input without comprehensive validation.

**Impact:**
- Potential for replay attacks, data injection, or request forgery

**Fix:**
```python
from pydantic import validator
import hmac
import hashlib

class WebhookRequestBody(BaseModel):
    # Define expected fields
    pass

    @validator('body')
    def validate_webhook(cls, v):
        # Implement signature verification if webhook uses HMAC
        # Example for Twilio webhook:
        # expected_signature = hashlib.sha256(
        #     (v + TWILIO_AUTH_TOKEN).encode()
        # ).hexdigest()
        # if not hmac.compare_digest(
        #     request.headers.get('X-Twilio-Signature', ''),
        #     expected_signature
        # ):
        #     raise ValueError('Invalid signature')
        return v
```

---

## SECURITY BEST PRACTICES OBSERVED

### Positive Findings:
1. **Secrets Management:** Uses environment variables (`os.getenv`) for sensitive data
2. **Authentication:** Uses FastAPI's `@requires` decorator for route protection
3. **CSRF Protection:** Implements CSRF middleware and token validation
4. **CORS:** Configures ALLOWED_HOSTS to prevent open redirect attacks
5. **Environment Validation:** Enforces HTTPS in production mode
6. **Database Security:** Uses Django ORM with parameterized queries
7. **File Upload Limits:** Implements entry size limits to prevent DoS

---

## RECOMMENDATIONS

### Immediate Actions (Critical):
1. **Remove hardcoded credentials** from `docker-compose.yml` - Replace with environment variables
2. **Fix eval() usage** in grounding_agent_uitars.py - Replace with `ast.literal_eval()` or strict validation
3. **Replace pickle with JSON** in migration files - Avoid insecure deserialization

### High Priority (Major):
4. **Sanitize subprocess arguments** - Remove `shell=True` and validate all inputs
5. **Strengthen CSP** - Remove `unsafe-inline` and `unsafe-eval` where possible
6. **Add path validation** - Implement strict validation for file paths and user input

### Medium Priority (Minor):
7. **Improve logging** - Add sensitive data filtering to log messages
8. **Validate webhooks** - Implement signature verification for all webhook handlers
9. **Review random number generation** - Ensure cryptographic random is used for security-sensitive operations

### Long-term Improvements:
10. **Security Testing:** Add comprehensive security testing in CI/CD pipeline
11. **Dependency Scanning:** Regularly audit dependencies for vulnerabilities using tools like Snyk, Dependabot, or npm audit
12. **Penetration Testing:** Conduct regular security audits by security professionals
13. **Security Headers:** Add additional security headers (X-Content-Type-Options, X-Frame-Options, etc.)
14. **Input Validation Framework:** Implement a centralized input validation framework
15. **Secret Rotation:** Implement secrets rotation mechanism for API keys and tokens

---

## DEPENDENCY VULNERABILITY ASSESSMENT

### Checked Dependencies (from pyproject.toml):

**Python Dependencies:**
- `fastapi >= 0.110.0` - Check for CVEs
- `openai >= 2.0.0, < 3.0.0` - Check for CVEs
- `anthropic == 0.75.0` - Specific version
- `google-genai == 1.52.0` - Specific version
- `e2b-code-interpreter ~= 1.0.0` - Check for CVEs
- `huggingface-hub[hf_xet] >= 0.22.2` - Check for CVEs
- `psycopg2-binary == 2.9.9` - Specific version

**Recommendation:**
Run full dependency security audit using:
```bash
# Python
pip-audit
safety check
pip-compile --upgrade --all-extras

# TypeScript
npm audit
yarn audit
```

---

## TESTING RECOMMENDATIONS

### Security Test Cases to Implement:
1. **Path Traversal Tests:** Test file operations with `../../../etc/passwd`, `../..`, etc.
2. **Command Injection Tests:** Test subprocess calls with `;rm -rf /`, `&&`, `|` commands
3. **XSS Tests:** Test web UI with malicious JavaScript payloads
4. **CSRF Tests:** Test form submissions with forged CSRF tokens
5. **SSRF Tests:** Test server-side request forgery in web search functionality
6. **Deserialization Tests:** Test pickle/unpickle with crafted payloads
7. **Authentication Tests:** Test unauthorized access to protected endpoints
8. **Rate Limiting Tests:** Test DoS protection mechanisms
9. **Input Validation Tests:** Test edge cases and boundary conditions
10. **Secret Leakage Tests:** Ensure no credentials in logs, responses, or code comments

---

## CONCLUSION

The Khoj codebase demonstrates good security practices in several areas, including proper authentication, CSRF protection, and secret management via environment variables. However, there are critical and major vulnerabilities that need immediate attention:

- **Critical:** Hardcoded credentials in production configuration
- **Major:** Unsafe eval() usage and pickle deserialization

The codebase should prioritize fixing the critical and major vulnerabilities before deploying to production. Additional improvements in input validation, CSP configuration, and logging hygiene will further enhance security posture.

**Overall Security Rating: 6/10**

**Risk Level:** Moderate
**Exposure:** High (codebase handles user data and potentially sensitive operations)

---

*Analysis performed by security scan on March 8, 2026*
*Tools used: grep, find, read*
