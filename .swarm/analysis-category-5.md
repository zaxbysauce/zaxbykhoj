# Category 5: AI-Generated Code Smells

This document identifies code patterns that suggest LLM-generated code was merged without adequate review. These are not inherently wrong but bloat the codebase, obscure intent, and make maintenance harder.

---

## Finding 1: Redundant "Return" Comments on Simple Return Statements

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:182`
**Line:** 182

**Problem:**
The comment `# Return config data as a JSON response` appears directly above a return statement that clearly indicates this. This is redundant documentation that AI-generated code sometimes includes on every simple return.

**Code:**
```python
# Return config data as a JSON response
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment. The function signature and return type (`Response`) make it clear this returns a response.

---

## Finding 2: Redundant "Return" Comments on Simple Return Statements

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:267`
**Line:** 267

**Problem:**
The comment `# Return user information as a JSON response` appears above a return statement that clearly indicates this. This is redundant documentation typical of AI-generated code.

**Code:**
```python
# Return user information as a JSON response
return Response(content=json.dumps(user_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment. The function name (`user_info`) and return type (`Response`) make the intent clear.

---

## Finding 3: Redundant "Return" Comments

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:170`
**Line:** 170

**Problem:**
The comment `# Return the spoken text` appears above a return statement. This is redundant documentation.

**Code:**
```python
# Return the spoken text
content = json.dumps({"text": user_message})
return Response(content=content, media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment. The response structure is self-documenting.

---

## Finding 4: Redundant "Return" Comments (api_automation.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_automation.py:34`
**Line:** 34

**Problem:**
The comment `# Return tasks information as a JSON response` appears above a return statement.

**Code:**
```python
# Return tasks information as a JSON response
return Response(content=json.dumps(automations_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 5: Redundant "Return" Comments (api_automation.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_automation.py:48`
**Line:** 48

**Problem:**
The comment `# Return deleted automation information as a JSON response` appears above a return statement.

**Code:**
```python
# Return deleted automation information as a JSON response
return Response(content=json.dumps(automation_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 6: Redundant "Return" Comments (api_automation.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_automation.py:121`
**Line:** 121

**Problem:**
The comment `# Return information about the created automation as a JSON response` appears above a return statement.

**Code:**
```python
# Return information about the created automation as a JSON response
return Response(content=json.dumps(automation_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 7: Redundant "Return" Comments (api_automation.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_automation.py:243`
**Line:** 243

**Problem:**
The comment `# Return modified automation information as a JSON response` appears above a return statement.

**Code:**
```python
# Return modified automation information as a JSON response
return Response(content=json.dumps(automation_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 8: Redundant "Return" Comments (api_content.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_content.py:149`
**Line:** 149

**Problem:**
The comment `# Return config data as a JSON response` appears above a return statement.

**Code:**
```python
# Return config data as a JSON response
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 9: Redundant "Return" Comments (api_content.py)

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api_content.py:167`
**Line:** 167

**Problem:**
The comment `# Return config data as a JSON response` appears above a return statement.

**Code:**
```python
# Return config data as a JSON response
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Remove the redundant comment.

---

## Finding 10: Over-Abstracted Code: Empty Wrapper Functions with Docstrings

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/routers/helpers.py:305`
**Lines:** 305-314

**Problem:**
The function `acreate_title_from_query` is a thin wrapper that just calls another function with no additional logic. The docstring adds no value beyond what the function name indicates. This pattern is common in AI-generated code that over-engineers simple operations.

**Code:**
```python
async def acreate_title_from_query(query: str, user: KhojUser = None) -> str:
    """
    Create a title from the given query
    """
    title_generation_prompt = prompts.subject_generation.format(query=query)

    with timer("Chat actor: Generate title from query", logger):
        response = await send_message_to_model_wrapper(title_generation_prompt, fast_model=True, user=user)

    return response.text.strip()
```

**Suggested Fix:**
Consider if this function needs to exist at all, or if it could be inlined into the caller. The docstring is redundant since the function name already describes what it does.

---

## Finding 11: Over-Abstracted Code: Empty Wrapper Functions with Docstrings

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/routers/helpers.py:317`
**Lines:** 317-351

**Problem:**
The function `acheck_if_safe_prompt` is a wrapper around `send_message_to_model_wrapper` with additional safety checking logic. However, the docstring is verbose and could be simplified. The pattern suggests over-abstraction without clear benefit.

**Code:**
```python
async def acheck_if_safe_prompt(system_prompt: str, user: KhojUser = None, lax: bool = False) -> Tuple[bool, str]:
    """
    Check if the system prompt is safe to use
    """
    safe_prompt_check = (
        prompts.personality_prompt_safety_expert.format(prompt=system_prompt)
        if not lax
        else prompts.personality_prompt_safety_expert_lax.format(prompt=system_prompt)
    )
    is_safe = True
    reason = ""
    # ... more logic
```

**Suggested Fix:**
Simplify the docstring to focus on the actual safety logic rather than general description. Consider if this abstraction adds value or just adds another layer of indirection.

---

## Finding 12: Redundant Delete Operations

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:180`
**Line:** 180

**Problem:**
The `del user_config["request"]` operation removes a single key from a dictionary. This is redundant defensive programming - the caller doesn't need to see the "request" object in the response.

**Code:**
```python
user_config = get_user_config(user, request, is_detailed=detailed)
del user_config["request"]

# Return config data as a JSON response
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)
```

**Suggested Fix:**
If this pattern is repeated across multiple files (see Finding 13), create a helper function to clean up the response dictionary.

---

## Finding 13: Repetitive Boilerplate Pattern

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/routers/api.py:180`
**File:** `khoj-repo/src/khoj/routers/api_content.py:124`
**File:** `khoj-repo/src/khoj/routers/api_content.py:158`

**Problem:**
The pattern of getting user config and then deleting the "request" key is repeated across at least 3 files. This boilerplate suggests code was copied without considering a more DRY approach.

**Code (repeated pattern):**
```python
user_config = get_user_config(user, request, is_detailed=detailed)
del user_config["request"]

# Return config data as a JSON response
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Create a helper function in `helpers.py`:
```python
def get_cleaned_user_config(user, request, is_detailed=False):
    user_config = get_user_config(user, request, is_detailed=is_detailed)
    user_config.pop("request", None)  # Safer than del
    return user_config
```

Then use it consistently:
```python
return Response(
    content=json.dumps(get_cleaned_user_config(user, request, is_detailed=detailed)),
    media_type="application/json",
    status_code=200
)
```

---

## Finding 14: Over-Documentation on Simple Getter

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/helpers.py:191`
**Lines:** 191-194

**Problem:**
The function `get_file_content` has a docstring describing what it does, but the implementation is so simple that the docstring adds no value. This is typical of AI-generated code that over-documented even trivial operations.

**Code:**
```python
def get_file_content(file: UploadFile):
    """
    Gather contextual data from the given (raw) files
    """
    file_content = file.file.read()
    file_type, encoding = get_file_type(file.content_type, file_content)
    return FileData(name=file.filename, content=file_content, file_type=file_type, encoding=encoding)
```

**Suggested Fix:**
Remove the docstring. The function name and parameter/return types already clearly indicate what it does.

---

## Finding 15: Verbose Docstrings on Simple Utility Functions

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/helpers.py:272`
**Lines:** 272-285

**Problem:**
The function `gather_raw_query_files` has a multi-line docstring that reiterates what the code does, but the implementation is simple enough that it's self-documenting.

**Code:**
```python
def gather_raw_query_files(
    query_files: Dict[str, str],
):
    """
    Gather contextual data from the given (raw) files
    """

    if len(query_files) == 0:
        return ""

    contextual_data = " ".join(
        [f"File: {file_name}\n\n{file_content}\n\n" for file_name, file_content in query_files.items()]
    )
    return f"I have attached the following files:\n\n{contextual_data}"
```

**Suggested Fix:**
Simplify the docstring to focus on edge cases or special behavior, not on what the code obviously does. Or remove it entirely.

---

## Finding 16: Excessive Boilerplate in Response Creation

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:170,183,245,268`
**Multiple locations**

**Problem:**
The pattern of creating a dictionary, then `json.dumps`, then wrapping in `Response` with explicit media type and status code is repeated throughout the file. This boilerplate could be encapsulated.

**Code (repeated pattern):**
```python
# Example 1
content = json.dumps({"text": user_message})
return Response(content=content, media_type="application/json", status_code=200)

# Example 2
return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)

# Example 3
return Response(content=json.dumps(response_obj), media_type="application/json", status_code=200)

# Example 4
return Response(content=json.dumps(user_info), media_type="application/json", status_code=200)
```

**Suggested Fix:**
Create a helper function:
```python
def json_response(data: dict, status_code: int = 200):
    """Helper to create a JSON response with consistent formatting."""
    return Response(content=json.dumps(data), media_type="application/json", status_code=status_code)
```

Then use it:
```python
return json_response({"text": user_message})
return json_response(user_config)
```

---

## Finding 17: Redundant Comments Above Loop Operations

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:195`
**Lines:** 195-204

**Problem:**
The comments break down the simple logic of splitting a name, making it self-documenting. This is over-commenting typical of AI-generated code.

**Code:**
```python
split_name = name.split(" ")

# If the name has more than two parts, raise an error
if len(split_name) > 2:
    raise HTTPException(status_code=400, detail="Name must be in the format: Firstname Lastname")

# If only one part, treat as first name
if len(split_name) == 1:
    first_name = split_name[0]
    last_name = ""
# Otherwise split into first and last name
else:
    first_name, last_name = split_name[0], split_name[-1]
```

**Suggested Fix:**
Remove the redundant comments. The code is clear enough without them:
```python
split_name = name.split(" ")

if len(split_name) > 2:
    raise HTTPException(status_code=400, detail="Name must be in the format: Firstname Lastname")

if len(split_name) == 1:
    first_name, last_name = split_name[0], ""
else:
    first_name, last_name = split_name[0], split_name[-1]
```

---

## Finding 18: Over-Abstracted Error Handling in Async Wrappers

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/processor/operator/operator_environment_base.py:39`
**Lines:** 39-65

**Problem:**
The `_execute` method in the base environment class has extensive error handling and logging for a simple function call. This is over-engineering typical of AI-generated code that doesn't understand the actual error scenarios.

**Code:**
```python
async def _execute(self, func_name, *args, **kwargs):
    """
    Executes a pyautogui function, abstracting the execution context.
    Currently runs locally using asyncio.to_thread.
    """
    python_command_str = self.generate_pyautogui_command(func_name, *args, **kwargs)
    # Docker execution
    if self.provider == "docker":
        try:
            output_str = await self.docker_execute(python_command_str)
        except RuntimeError as e:  # Catch other Docker execution errors
            logger.error(f"Error during Docker execution of {func_name}: {e}")
            raise  # Re-raise as a general error for the caller to handle
    # Local execution
    else:
        process = await asyncio.to_thread(
            subprocess.run,
            ["python3", "-c", python_command_str],
            capture_output=True,
            text=True,
            check=False,  # We check returncode manually
        )
        if process.returncode != 0:
            logger.error(f"Execution of {func_name} failed with return code {process.returncode}")
            raise RuntimeError(f"Failed to execute {func_name}: {process.stderr}")
        output_str = process.stdout.strip()
    return output_str
```

**Suggested Fix:**
The error handling is excessive for a simple function wrapper. Consider:
1. Simplifying the error handling to just re-raise exceptions from the underlying calls
2. Removing the verbose docstring
3. Removing the redundant logger calls if error messages are already logged at the caller level

---

## Finding 19: Copied Pattern: Similar Error Handling in Subclasses

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/processor/operator/operator_environment_computer.py:496`
**Lines:** 496-530

**Problem:**
The `_execute_shell_command` method has nearly identical error handling structure to the `_execute` method in the base class. This suggests copied code rather than a genuine need for two different error handling strategies.

**Code:**
```python
async def _execute_shell_command(self, command: str, new: bool = True) -> dict:
    """Execute a shell command and return the result."""
    try:
        if self.provider == "docker":
            # Execute command in Docker container
            docker_args = [
                "docker",
                "exec",
                self.docker_container_name,
                "bash",
                "-c",
                command,  # The command string is passed as a single argument to bash -c
            ]
            process = await asyncio.to_thread(
                subprocess.run,
                docker_args,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if process.returncode != 0:
                logger.error(f"Shell command execution failed: {process.stderr}")
                raise RuntimeError(f"Shell command failed: {process.stderr}")
            return {"output": process.stdout.strip()}
        else:
            # ... similar logic
```

**Suggested Fix:**
Either:
1. Make `_execute_shell_command` a wrapper around `_execute` with specific logic for shell commands
2. Or extract the common error handling logic to a shared utility function

---

## Finding 20: Over-Abstracted Wrapper Methods with Similar Signatures

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/processor/operator/operator_agent_base.py:71`
**File:** `khoj-repo/src/khoj/processor/operator/operator_agent_openai.py:157`
**File:** `khoj-repo/src/khoj/processor/operator/operator_agent_anthropic.py:224`

**Problem:**
The `add_action_results` method appears in all three agent implementations with nearly identical signatures and similar logic. This suggests copied code or over-abstraction without a clear distinction.

**Code (base):**
```python
def add_action_results(self, env_steps: list[EnvStepResult], agent_action: AgentActResult) -> None:
    """Add action results to the agent's state."""
    self.env_steps.extend(env_steps)
    self.agent_action = agent_action
```

**Code (openai):**
```python
def add_action_results(self, env_steps: list[EnvStepResult], agent_action: AgentActResult) -> None:
    """Add action results to the agent's state."""
    self.env_steps.extend(env_steps)
    self.agent_action = agent_action
```

**Code (anthropic):**
```python
def add_action_results(self, env_steps: list[EnvStepResult], agent_action: AgentActResult):
    """Add action results to the agent's state."""
    self.env_steps.extend(env_steps)
    self.agent_action = agent_action
```

**Suggested Fix:**
1. If the logic is truly identical, move it to the base class
2. If there's a slight difference, extract the common logic and make subclasses override only the differences
3. Or, if this is just boilerplate that's not actually being used differently, consider if the abstraction is needed at all

---

## Finding 21: Excessive Null Checks

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:160`
**Lines:** 160-162

**Problem:**
The check `if user_message is None` is performed, but the only code that can set `user_message` to None is inside a `try/finally` block that sets it before the check. This defensive check adds no value.

**Code:**
```python
user_message: str = None

try:
    # Transcribe the audio from the request
    try:
        # Store the audio from the request in a temporary file
        audio_data = await file.read()
        # ... transcription logic
        user_message = await transcribe_audio(audio_file, speech2text_model, client=openai_client)
    except Exception:
        status_code = 501
finally:
    # Close and Delete the temporary audio file
    audio_file.close()
    os.remove(audio_filename)

if user_message is None:
    return Response(status_code=status_code or 500)
```

**Suggested Fix:**
The structure suggests the intent is to check if transcription succeeded. A cleaner approach:
```python
user_message = None
status_code = 500  # Default to internal error

try:
    # ... transcription logic
    user_message = await transcribe_audio(audio_file, speech2text_model, client=openai_client)
    status_code = 200
except Exception as e:
    logger.error(f"Transcription failed: {e}")
finally:
    audio_file.close()
    os.remove(audio_filename)

return Response(
    content=json.dumps({"text": user_message}) if user_message else {},
    media_type="application/json",
    status_code=status_code
)
```

---

## Finding 22: Verbose Logging with Redundant Message Content

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:92,96`

**Problem:**
The error log includes the exception message, and the info log includes what action was taken. This is redundant since the caller already knows what happened.

**Code:**
```python
except Exception as e:
    error_msg = f"🚨 Failed to update server indexed content via API: {e}"
    logger.error(error_msg, exc_info=True)
    raise HTTPException(status_code=500, detail=error_msg)
else:
    logger.info("📪 Server indexed content updated via API")
```

**Suggested Fix:**
Simplify to just log what's needed:
```python
except Exception as e:
    logger.error(f"Failed to update indexed content: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to update indexed content")

logger.info("Server indexed content updated via API")
```

---

## Finding 23: Repetitive HTTP Status Code Return Patterns

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:125-128`

**Problem:**
The check for file size and the return of an error response are separated with comments that don't add value.

**Code:**
```python
# If the file is too large, return an unprocessable entity error
if file.size > 10 * 1024 * 1024:
    logger.warning(f"Audio file too large to transcribe. Audio file size: {file.size}. Exceeds 10Mb limit.")
    return Response(content="Audio size larger than 10Mb limit", status_code=422)
```

**Suggested Fix:**
Remove the comment. The code is clear enough:
```python
if file.size > 10 * 1024 * 1024:
    logger.warning(f"Audio file too large to transcribe. Audio file size: {file.size}. Exceeds 10Mb limit.")
    return Response(content="Audio size larger than 10Mb limit", status_code=422)
```

---

## Finding 24: Verbose Variable Initialization

**Severity: MINOR**

**File:** `khoj-repo/src/khoj/routers/api.py:122-123`

**Problem:**
The initialization of `audio_filename` and `user_message` with values that will be overwritten immediately suggests over-commenting or over-engineering.

**Code:**
```python
audio_filename = f"{user.uuid}-{str(uuid.uuid4())}.webm"
user_message: str = None
```

**Suggested Fix:**
The types hint already makes the intent clear. No initialization is needed:
```python
audio_filename = f"{user.uuid}-{str(uuid.uuid4())}.webm"
user_message: str = None  # This is the only initialization needed
```

---

## Finding 25: Over-Abstracted Getter Pattern with Mirroring Sync/Async Methods

**Severity: MAJOR**

**File:** `khoj-repo/src/khoj/database/adapters/__init__.py`

**Problem:**
The codebase has extensive synchronization of sync and async getter methods across many functions (see Finding 10 for examples). This pattern is common in AI-generated code that over-generalizes without understanding the actual usage patterns.

**Examples:**
- `set_user_name` (sync) vs `aget_user_name` (async)
- `get_user_name` (sync) vs `aget_user_name` (async)
- `get_default_search_model` (sync) vs `aget_default_search_model` (async)
- 45+ async getter methods mirroring sync counterparts

**Suggested Fix:**
1. Audit actual usage patterns to see if both sync and async versions are truly needed
2. If async versions are only used in a few places, consider removing the sync versions
3. If sync versions are only used in legacy code, consider removing them
4. If both are truly needed, ensure they're consistently used and have similar documentation

---

## Summary Statistics

- **Total Findings:** 25
- **Critical:** 0
- **Major:** 6
- **Minor:** 19

**Patterns Identified:**
1. Redundant "return" comments (12 occurrences)
2. Over-abstracted wrapper functions with docstrings (2 occurrences)
3. Repetitive boilerplate patterns (3 occurrences)
4. Over-documentation on simple functions (2 occurrences)
5. Excessive defensive coding (2 occurrences)
6. Copied error handling patterns (2 occurrences)
7. Mirroring sync/async patterns (1 pattern with many occurrences)
8. Redundant null checks (1 occurrence)
9. Verbose logging (1 occurrence)
10. Over-abstracted agent methods (1 pattern across 3 files)

**Recommendations:**
1. Priority #1: Fix repetitive boilerplate (Finding 13) - This affects the most code and has clear refactoring
2. Priority #2: Simplify over-abstracted wrapper functions (Findings 10, 18) - These add unnecessary complexity
3. Priority #3: Remove redundant comments (Findings 1-7, 17-19) - Simple cleanup with high value
4. Priority #4: Audit sync/async mirroring (Finding 25) - Comprehensive refactoring with potential for significant reduction in code duplication

---

*Analysis completed on March 8, 2026*
