# Category 4: Stale Comments & Documentation Drift Analysis
## Analysis Date: 2026-03-08

This analysis identifies comments and documentation that no longer match the actual code behavior or state of the Khoj codebase.

---

## CRITICAL FINDINGS

### 1. Migration Rollback Documentation May Be Outdated
**File:** `./docs/migration_rollback.md`
**Lines:** 1-603 (entire document)

**Problem:**
The migration rollback documentation describes procedures for migrations 0099, 0100, 0101, and 0102, but these migrations may no longer be the most recent. The documentation states the document is valid for these migrations, but doesn't account for newer migrations (0103, 0104, 0105, 0106, 0107) that exist in the codebase.

**Severity:** CRITICAL
**Impact:** Documentation contains incorrect information about which migrations can be rolled back. Following these instructions could lead to attempting to rollback migrations that don't exist in the current database state, causing confusion or errors.

**Evidence:**
```bash
# Actual migrations in codebase:
0090_alter_khojuser_uuid.py
0091_chatmodel_friendly_name_and_more.py
0092_alter_chatmodel_model_type_alter_chatmodel_name_and_more.py
0093_remove_localorgconfig_user_and_more.py
0094_serverchatsettings_think_free_deep_and_more.py
0095_alter_webscraper_type.py
0096_mcpserver.py
0097_serverchatsettings_priority.py
0098_alter_texttoimagemodelconfig_model_type.py
0099_usermemory.py
0100_add_search_vector.py
0101_add_context_summary.py
0102_add_chunk_scale.py
0103_add_ldap_dn_to_user.py
0104_ldap_config.py
0105_add_hybrid_fields.py
0106_add_ldap_dn.py
0107_alter_entry_embeddings.py
```

**Suggested Fix:**
- Update migration_rollback.md to reflect current migration state
- Add migration chain diagram showing all migrations (0099-0107)
- Include rollback procedures for the newer migrations (0103-0107) if they have dependencies
- Remove or update outdated migration references
- Update "Last Updated: 2026-03-07" to current date

---

## MAJOR FINDINGS

### 2. Outdated Deprecated Parameter Documentation
**File:** `./khoj-repo/src/khoj/processor/content/text_to_entries.py`
**Lines:** 75

**Problem:**
The docstring for `chunk_entries()` documents that `max_tokens` parameter is "Deprecated. Use chunk_sizes instead. Single chunk size for backward compatibility." However, this documentation doesn't explicitly state:
- Whether the deprecated parameter is still being used in production
- When it will be removed
- Whether there's a migration plan to remove users of this parameter

**Severity:** MAJOR
**Impact:** Developers relying on this documentation may not be aware of the deprecation timeline or may not understand the implications of continuing to use the deprecated parameter.

**Evidence:**
```python
# Line 75
max_tokens: Deprecated. Use chunk_sizes instead. Single chunk size for backward compatibility.
```

**Suggested Fix:**
- Add deprecation warning to documentation with a clear removal timeline
- Update to include: "This parameter is scheduled for removal in version X. Migrate to chunk_sizes by version Y."
- Consider removing the backward compatibility path entirely if not critical

---

### 3. Outdated TODO Comments for Feature Gaps
**File:** `./khoj-repo/src/khoj/processor/operator/__init__.py`
**Lines:** 83, 95

**Problem:**
The TODO comments state "Remove once OpenAI Operator Agent is useful" and "Remove once Binary Operator Agent is useful", but these features are disabled with `if False:` checks, indicating they are not expected to be implemented. The comments suggest these features are "coming soon" but they are actively being blocked from executing.

**Severity:** MAJOR
**Impact:** Comments mislead developers into thinking these features are planned for future implementation, when they are actually disabled with `if False:` checks.

**Evidence:**
```python
# Line 83
# TODO: Remove once OpenAI Operator Agent is useful

# Line 95
# TODO: Remove once Binary Operator Agent is useful

# Lines 84-95
elif is_operator_model(reasoning_model.name) == ChatModel.ModelType.OPENAI and False:
    operator_agent = OpenAIOperatorAgent(...)
elif False:
    grounding_model_name = "ui-tars-1.5"
    grounding_model = await ConversationAdapters.aget_chat_model_by_name(grounding_model_name)
    if (
        not grounding_model
        or not grounding_model.vision_enabled
        or not grounding_model.model_type == ChatModel.ModelType.OPENAI
    ):
        raise ValueError("Binary operator agent needs ui-tars-1.5 served over an OpenAI compatible API.")
    operator_agent = BinaryOperatorAgent(...)
```

**Suggested Fix:**
- Replace with: "Note: OpenAI Operator Agent and Binary Operator Agent are not currently enabled. See issue #XXXX for details."
- Remove the TODO comments and instead explain why these agents are disabled
- If these features are truly experimental and never planned for production, consider removing the disabled code paths entirely

---

### 4. Unimplemented Feature in Notion Integration
**File:** `./khoj-repo/src/khoj/processor/content/notion/notion_to_entries.py`
**Line:** 108

**Problem:**
The code has a TODO comment indicating databases are not yet handled in the Notion integration, but there's no corresponding implementation or error handling for database objects.

**Severity:** MAJOR
**Impact:** The integration silently skips database content, which may lead to incomplete data indexing. Users may expect database content to be indexed but receive no results.

**Evidence:**
```python
# Line 108
if p_or_d["object"] == "database":
    # TODO: Handle databases
    continue
```

**Suggested Fix:**
- Either implement database handling or clearly document that database content is not supported
- Add a warning log when database objects are encountered
- Update user-facing documentation to clarify supported Notion content types

---

## MINOR FINDINGS

### 5. Future Optimization TODO
**File:** `./khoj-repo/src/interface/web/app/components/chatHistory/chatHistory.tsx`
**Line:** 357

**Problem:**
This TODO comments about a future optimization but doesn't provide context about when it might be implemented or why it's currently deferred.

**Severity:** MINOR
**Impact:** Minimal - this is a genuine optimization suggestion, but the comment lacks context.

**Evidence:**
```typescript
// Line 357
// TODO: A future optimization would be to add a time to delay to re-enabling the intersection observer.
```

**Suggested Fix:**
- Add context about why this optimization hasn't been implemented yet (e.g., resource constraints, complexity, risk of regression)
- Consider removing if the current behavior is acceptable and the optimization is unlikely to be implemented soon

---

### 6. Theme Detection Function TODO
**File:** `./khoj-repo/src/interface/web/app/components/excalidraw/excalidrawWrapper.tsx`
**Line:** 149

**Problem:**
Similar to #5, this is a legitimate TODO but lacks context.

**Severity:** MINOR
**Impact:** Minimal

**Evidence:**
```typescript
// Line 149
// TODO - Create a common function to detect if the theme is dark?
```

**Suggested Fix:**
- Add context about why a common function isn't being used yet
- If this is a general utility, consider implementing it to reduce code duplication

---

### 7. Hacky Code Comment
**File:** `./khoj-repo/src/khoj/utils/initialization.py`
**Line:** 217

**Problem:**
The comment acknowledges code is "hacky" but doesn't indicate when it will be replaced.

**Severity:** MINOR
**Impact:** Low - this is a legitimate code review comment, but might be resolved by a future refactor.

**Evidence:**
```python
# Line 217
# TODO: This is hacky. Will be replaced with more robust solution based on provider type enum
```

**Suggested Fix:**
- Remove the comment if it's outdated, or
- Include a version or issue number tracking the planned refactoring

---

### 8. Legacy Copyright Comment in Third-Party Code
**File:** `./khoj-repo/src/khoj/processor/content/org_mode/orgnode.py`
**Line:** 26

**Problem:**
The file contains a copyright notice from 2009 that states "Added support for all tags, TODO priority and checking existence of a tag". While this was the original functionality, the comment is now a historical artifact.

**Severity:** MINOR
**Impact:** Minimal - purely informational and doesn't affect code behavior.

**Evidence:**
```python
# Line 26
#   Added support for all tags, TODO priority and checking existence of a tag
```

**Suggested Fix:**
- Consider removing if no longer relevant, or
- Update to reflect current capabilities

---

### 9. Insufficient Validation Comment
**File:** `./khoj-repo/src/khoj/routers/helpers.py`
**Line:** 973

**Problem:**
A comment indicates additional validation is needed for Excalidraw diagram validation, but no clear action plan is provided.

**Severity:** MINOR
**Impact:** Low - this is a code review suggestion, not a blocking issue.

**Evidence:**
```python
# Line 973
# TODO Some additional validation here that it's a valid Excalidraw diagram
```

**Suggested Fix:**
- Add context about validation approach
- If validation is critical, implement it; otherwise, remove the comment

---

### 10. Sync Version Comment
**File:** `./khoj-repo/src/khoj/processor/conversation/google/utils.py`
**Line:** 425

**Problem:**
A comment about generation being "in progress" references a specific check but lacks context about why this check is needed.

**Severity:** MINOR
**Impact:** Minimal

**Evidence:**
```python
# Line 425
# Check if finish reason is empty, therefore generation is in progress
```

**Suggested Fix:**
- Add more context about the purpose of this check
- Remove if the comment is redundant with the code

---

### 11. Incomplete Implementation in Database Adapters
**File:** `./khoj-repo/src/khoj/database/adapters/__init__.py`
**Line:** 736

**Problem:**
A TODO comment references a future update to allow any public agent once launched, but the current implementation restricts agents further with `managed_by_admin=True`.

**Severity:** MINOR
**Impact:** Low - this is a legitimate feature planning comment.

**Evidence:**
```python
# Line 736
# TODO Update this to allow any public agent that's officially approved once that experience is launched
```

**Suggested Fix:**
- Add context about when this feature is expected to launch
- Remove if the TODO is outdated

---

### 12. Incomplete Agent Tool Configuration
**File:** `./khoj-repo/documentation/docs/advanced/admin.md`
**Line:** 18

**Problem:**
The documentation states "This field is not currently configurable and only supports all tools (i.e `["*"]`)", but doesn't provide context about why tools aren't individually configurable or when they might be.

**Severity:** MINOR
**Impact:** User confusion about agent configuration capabilities.

**Evidence:**
```markdown
# Line 18
- `Tools`: The list of tools available to this agent. Tools include notes, image, online. This field is not currently configurable and only supports all tools (i.e `["*"]`)
```

**Suggested Fix:**
- Add more context about the reasoning behind this limitation
- Update if/when per-tool configuration is planned

---

### 13. No Changelog Available
**Problem:**
The codebase doesn't appear to have a CHANGELOG.md file that would help track feature additions, deprecations, and changes over time.

**Severity:** MINOR
**Impact:** Developers may not know what features have been added, removed, or changed.

**Evidence:**
Searched for CHANGELOG.md and found no results in the main repository.

**Suggested Fix:**
- Consider implementing a CHANGELOG.md or maintain one in the repository
- Update it regularly with significant changes

---

### 14. Outdated Examples in Documentation
**File:** `./khoj-repo/documentation/docs/clients/obsidian.md`
**Lines:** 31-33

**Problem:**
Documentation references creating an API key at https://app.khoj.dev/settings#clients, but this URL may have changed with recent updates to the UI.

**Severity:** MINOR
**Impact:** Users may not be able to find the API key setting.

**Evidence:**
```markdown
# Lines 31-33
3. Generate an API key on the [Khoj Web App](https://app.khoj.dev/settings#clients)
4. Set your Khoj API Key in the Khoj plugin settings on Obsidian
```

**Suggested Fix:**
- Verify the URL is still correct
- Update to point to the correct location

---

## SUMMARY

### Issues by Severity:
- **CRITICAL:** 1 (migration rollback documentation)
- **MAJOR:** 3 (deprecated parameter, operator agent TODOs, Notion database handling)
- **MINOR:** 10 (various TODOs and documentation issues)

### Recommendations:
1. **Immediate Action:** Update migration rollback documentation to reflect current migration state
2. **Short-term:** Remove or properly document the disabled operator agent code paths
3. **Medium-term:** Implement or remove the Notion database handling and add clear documentation
4. **Long-term:** Review and update all TODO comments to include context or remove them

### Files Requiring Review:
- `./docs/migration_rollback.md`
- `./khoj-repo/src/khoj/processor/content/text_to_entries.py`
- `./khoj-repo/src/khoj/processor/operator/__init__.py`
- `./khoj-repo/src/khoj/processor/content/notion/notion_to_entries.py`
- `./khoj-repo/src/khoj/processor/content/org_mode/orgnode.py`

### Files with Multiple Issues:
- Multiple TODO/FIXME comments scattered across the codebase
- Documentation files with outdated examples and missing context
