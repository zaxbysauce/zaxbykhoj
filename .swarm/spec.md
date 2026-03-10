# Comprehensive Codebase Review Specification
Version: 2.0 | Date: 2026-03-08

---

## Feature Overview

This specification defines the process for conducting a comprehensive codebase audit and remediation on the Khoj project. The goal is to identify and fix problems in existing shipped code across 7 analysis categories.

---

## FR-001: Full Codebase Inventory
**MUST** produce a complete inventory of all source files, configuration files, test files, build files, CI/CD files, documentation files, and dotfiles in the project.

**Acceptance Criteria (SC-001):**
- GIVEN a request to audit the codebase
- WHEN the inventory process completes
- THEN `.swarm/codebase-inventory.md` exists
- AND contains tech stack (languages, frameworks, build system, test frameworks, package manager, runtime)
- AND contains file inventory (counts by type)
- AND contains architecture overview (entry points, module structure, dependency graph)
- AND contains patterns observed (conventions, error handling, logging, config loading, test patterns)

**Acceptance Criteria (SC-002):**
- GIVEN the codebase inventory
- WHEN the Architect reviews it
- THEN all source files are accounted for (not sampled)
- AND the Architect has read the inventory before proceeding to analysis

---

## FR-002: Deep Code Analysis
**MUST** perform deep analysis across 7 categories with findings that reference specific file paths and line numbers.

### FR-002-A: Broken/Missing/Incomplete Code Detection
**MUST** identify code that does not work as intended or is not finished.

**Acceptance Criteria (SC-003):**
- GIVEN the codebase
- WHEN analysis runs
- THEN findings include: functions with NotImplementedError, hardcoded stubs, empty bodies
- AND findings include: TODO/FIXME/HACK/XXX/PLACEHOLDER comments with status (completed vs incomplete)
- AND findings include: commented-out code blocks >5 lines
- AND findings include: unused interfaces/types/classes
- AND findings include: feature flags that always resolve one way
- AND findings include: silent exception swallowing
- AND findings include: missing switch cases
- AND findings include: unwired API routes/CLI commands
- AND findings include: empty or skipped test files
- AND findings include: functions with unused parameters

### FR-002-B: Security & Data Handling Analysis
**MUST** identify vulnerabilities, unsafe patterns, and data handling issues.

**Acceptance Criteria (SC-004):**
- GIVEN the codebase
- WHEN security analysis runs
- THEN findings include: hardcoded secrets, API keys, tokens, credentials
- AND findings include: missing input validation at system boundaries
- AND findings include: path traversal vulnerabilities
- AND findings include: command injection vectors
- AND findings include: unsafe deserialization
- AND findings include: missing auth/authorization checks
- AND findings include: sensitive data leakage in logs
- AND findings include: dependency vulnerabilities (outdated packages with CVEs)
- AND findings include: insufficient randomness for security operations
- AND findings include: missing CSRF/XSS/injection protections
- AND findings include: .gitignore gaps exposing sensitive files

### FR-002-C: Cross-Platform & Environment Analysis
**MUST** identify code that works on one platform but breaks on others.

**Acceptance Criteria (SC-005):**
- GIVEN the codebase
- WHEN cross-platform analysis runs
- THEN findings include: hardcoded path separators (using / or \\ instead of path.join)
- AND findings include: platform-specific shell commands
- AND findings include: incorrect process.cwd() usage
- AND findings include: case-sensitive file lookups on case-insensitive filesystems
- AND findings include: line ending assumptions
- AND findings include: environment variable assumptions (HOME vs USERPROFILE)
- AND findings include: unreliable file watching without polling fallback
- AND findings include: hard dependency on Unix tools
- AND findings include: assumed Unix directory structures (/tmp, /dev/null)

### FR-002-D: Stale Comments & Documentation Drift
**MUST** identify comments and documentation that no longer match the code.

**Acceptance Criteria (SC-006):**
- GIVEN the codebase
- WHEN documentation analysis runs
- THEN findings include: stale TODO/scaffold/stub comments on implemented code
- AND findings include: docstrings describing different behavior than actual
- AND findings include: README sections referencing removed/changed features
- AND findings include: changelog inconsistencies
- AND findings include: wrong configuration documentation
- AND findings include: outdated architecture diagrams
- AND findings include: completed ticket references in comments
- AND findings include: outdated documentation examples

### FR-002-E: AI-Generated Code Smells
**MUST** identify patterns indicating LLM-generated code was merged without adequate review.

**Acceptance Criteria (SC-007):**
- GIVEN the codebase
- WHEN AI code smell analysis runs
- THEN findings include: wrapper functions adding no logic
- AND findings include: comments that restate the code
- AND findings include: unnecessary docstrings on trivial functions
- AND findings include: excessive defensive coding already prevented by type system
- AND findings include: patterns that don't fit context (async where sync suffices)
- AND findings include: repeated boilerplate that should be shared utilities
- AND findings include: over-abstracted code (excessive indirection layers)
- AND findings include: generated code contradicting established patterns

### FR-002-F: Technical Debt & Architecture Issues
**MUST** identify structural and architectural issues that increase change costs.

**Acceptance Criteria (SC-008):**
- GIVEN the codebase
- WHEN architecture analysis runs
- THEN findings include: circular dependencies
- AND findings include: god objects/functions >100 lines with multiple responsibilities
- AND findings include: duplicated logic that should be shared utilities
- AND findings include: inconsistent patterns across modules
- AND findings include: hardcoded values that should be configuration
- AND findings include: missing or broken tests on critical paths
- AND findings include: tight coupling across module boundaries
- AND findings include: missing error boundaries/retry logic in I/O
- AND findings include: memory leaks (event listeners, intervals, unbounded caches)
- AND findings include: state management without enforced lifecycle (missing cleanup/disposal)

### FR-002-G: Performance & Enhancement Opportunities
**MUST** identify improvements that make the codebase better without changing external behavior.

**Acceptance Criteria (SC-009):**
- GIVEN the codebase
- WHEN performance analysis runs
- THEN findings include: N+1 queries or repeated I/O in loops
- AND findings include: synchronous I/O in hot paths
- AND findings include: missing caching for expensive repeated computations
- AND findings include: type safety gaps (any types, missing generics)
- AND findings include: missing observability in critical paths
- AND findings include: input validation gaps beyond security
- AND findings include: unused language/framework features
- AND findings include: bundle size/startup time optimization opportunities

---

## FR-003: SME Consultations
**MUST** consult subject matter experts for domain-specific best practices based on findings.

**Acceptance Criteria (SC-010):**
- GIVEN the tech stack from Step 0
- AND findings from Step 1
- WHEN SME consultations run
- THEN at minimum: primary language/framework SME is consulted
- AND security SME is consulted for any auth/network/file I/O/user input findings
- AND testing SME is consulted for test framework and coverage expectations
- AND domain-specific SME is consulted if applicable to the project

**Acceptance Criteria (SC-011):**
- GIVEN SME consultations
- WHEN complete
- THEN all guidance is captured in `.swarm/context.md`
- AND each entry includes: what was asked, what guidance was returned, how it applies to specific findings

---

## FR-004: Findings Report
**MUST** compile all findings into a structured report with classification.

**Acceptance Criteria (SC-012):**
- GIVEN all findings from Step 1
- WHEN compiling the report
- THEN each finding includes: ID (sequential within category), Category (1-7), Severity (CRITICAL/MAJOR/MINOR), File:Line, Problem, Fix, Size (S/M/L)
- AND counts summary is included at the top by category and severity
- AND report is written to `.swarm/context.md`

---

## FR-005: Implementation Plan
**MUST** convert findings into a phased implementation plan.

**Acceptance Criteria (SC-013):**
- GIVEN findings report
- WHEN drafting the plan
- THEN Phase 1 contains: all CRITICAL findings, security vulnerabilities, anything blocking correct operation
- AND Phase 2 contains: MAJOR findings that unblock other work or have cascading effects
- AND Phase 3 contains: remaining MAJOR findings, refactoring targets, cross-cutting concerns
- AND Phase 4 contains: MINOR findings, enhancements, documentation cleanup

**Acceptance Criteria (SC-014):**
- GIVEN the implementation plan
- WHEN written
- THEN each task includes: ID, title, Finding IDs addressed, Agent assignment, Files involved, Specific change description, Acceptance criteria, Dependencies
- AND tasks >6 files are split with subtask boundaries
- AND each CODER task is followed by QA review task

---

## FR-006: Plan Review (Critic Gate)
**MUST** pass the implementation plan through critic review before execution.

**Acceptance Criteria (SC-015):**
- GIVEN the implementation plan
- WHEN submitted to Critic
- THEN Critic evaluates: accuracy (file paths and line numbers check out), categorization (correct severity), completeness (no obvious misses), phasing (dependencies respected), actionability (clear enough for coder), size (no too-large or too-small tasks), coverage (acceptance criteria verify the fix)

**Acceptance Criteria (SC-016):**
- GIVEN Critic review
- WHEN verdict is NEEDS_REVISION
- THEN the plan is revised and resubmitted (max 2 cycles)
- AND if still not approved after 2 revisions, unresolved concerns are noted and execution proceeds

---

## FR-007: User Presentation
**MUST** present the findings and plan to the user for approval before implementation.

**Acceptance Criteria (SC-017):**
- GIVEN the plan is approved (or max revision cycles reached)
- WHEN presenting to user
- THEN summary table shows finding counts by category and severity
- AND critical findings list shows every CRITICAL finding with one-line description
- AND phased plan overview shows phase titles, task counts, estimated scope
- AND architect recommendations are included if any
- AND questions/decisions requiring user input are surfaced

---

## Edge Cases

1. **Large Codebases**: For codebases with many files, parallelize Explorer delegations by directory subtree
2. **Vague Findings**: If a finding cannot reference a specific file and line number, it is not a finding
3. **Stale Comments**: Determine if TODO/FIXME work was completed (comment stale) or genuinely incomplete
4. **SME Confidence**: If SME returns LOW confidence, do NOT consume directly - either re-delegate or flag as unverified

---

## Key Entities

- Codebase Inventory (output: `.swarm/codebase-inventory.md`)
- Findings Report (output: `.swarm/context.md`)
- Implementation Plan (output: `.swarm/plan.md`)
- SME Guidance (cached in: `.swarm/context.md`)

---

## [RESOLVED] Clarifications

1. **Scope Boundary**: Review only project's own source code, configuration, and test files. Exclude node_modules/, vendor/, .git/, dist/, build/, __pycache__, .venv/, *.pyc, .pytest_cache/, node_modules/, .tox/ (standard exclusions for code review).

2. **Historical Context**: No knowledge.jsonl or evidence files exist in .swarm/. No prior findings to check - starting fresh.

3. **Existing Context Files**: The previous context.md from the "paid" swarm (Khoj Authentication Enhancement project) has been archived to `.swarm/spec-archive/context-v1-paid-swarm-2026-03-07.md`. Context is now clear for new findings.
