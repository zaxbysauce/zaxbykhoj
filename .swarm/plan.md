<!-- PLAN_HASH: 2vj650a36mzif -->
# Comprehensive Codebase Review - Khoj
Swarm: lowtier
Phase: 1 [PENDING] | Updated: 2026-03-10T21:17:17.866Z

---
## Phase 1: Codebase Ingest & Inventory [PENDING]
- [ ] 1.1: Delegate Explorer to read every source file and build complete inventory [LARGE]

---
## Phase 2: Deep Code Analysis [PENDING]
- [ ] 2.1: Analyze Category 1: Broken/Incomplete Code [LARGE]
- [ ] 2.2: Analyze Category 2: Security & Data Handling [LARGE]
- [ ] 2.3: Analyze Category 3: Cross-Platform Issues [LARGE]
- [ ] 2.4: Analyze Category 4: Stale Comments & Docs [LARGE]
- [ ] 2.5: Analyze Category 5: AI Code Smells [LARGE]
- [ ] 2.6: Analyze Category 6: Tech Debt & Architecture [LARGE]
- [ ] 2.7: Analyze Category 7: Performance [LARGE]

---
## Phase 3: SME Consultations [PENDING]
- [ ] 3.1: Consult Python/Django SME [MEDIUM]
- [ ] 3.2: Consult Security SME [MEDIUM]
- [ ] 3.3: Consult Testing SME [MEDIUM]

---
## Phase 4: Compile & Classify Findings [PENDING]
- [ ] 4.1: Compile findings into structured report [LARGE]

---
## Phase 5: Critical Security Fixes [PENDING]
- [ ] 5.1: Remove hardcoded credentials from docker-compose.yml [SMALL]
- [ ] 5.2: Replace unsafe eval() with ast.literal_eval [MEDIUM]
- [ ] 5.3: Replace pickle with JSON in migrations [SMALL]
- [ ] 5.4: Replace shell=True with shell=False [MEDIUM]
- [ ] 5.5: Add path traversal validation [MEDIUM]

---
## Phase 6: Critical Cross-Platform Fixes [PENDING]
- [ ] 6.1: Replace hardcoded /home/user with os.path.expanduser [SMALL]
- [ ] 6.2: Replace find command with pathlib [MEDIUM]
- [ ] 6.3: Replace head command with pathlib [MEDIUM]
- [ ] 6.4: Replace sed command with pathlib [MEDIUM]
- [ ] 6.5: Fix tilde path expansion [SMALL]
- [ ] 6.6: Replace /tmp/uvicorn.sock with tempfile.gettempdir [SMALL]

---
## Phase 7: Critical Architecture - Circular Dependencies [PENDING]
- [ ] 7.1: Extract ai_update_memories to common/ [MEDIUM]
- [ ] 7.2: Extract image helpers to common/ [MEDIUM]
- [ ] 7.3: Extract binary agent helpers to common/ [MEDIUM]

---
## Phase 8: Critical Architecture - God Object Refactor [PENDING]
- [ ] 8.1: Create auth_helpers.py [MEDIUM] (depends: 7.1, 7.2, 7.3)
- [ ] 8.2: Create search_helpers.py [MEDIUM] (depends: 7.1, 7.2, 7.3)
- [ ] 8.3: Create vector_helpers.py [MEDIUM] (depends: 7.1, 7.2, 7.3)
- [ ] 8.4: Update helpers.py facade [SMALL] (depends: 8.1, 8.2, 8.3)

---
## Phase 9: Critical Architecture - Error Boundaries [PENDING]
- [ ] 9.1: Add retry to api_chat.py [SMALL]
- [ ] 9.2: Add retry to api.py [SMALL]
- [ ] 9.3: Add global exception handler [SMALL]

---
## Phase 10: Critical Performance Fixes [PENDING]
- [ ] 10.1: Fix N+1 query with bulk operations [MEDIUM]
- [ ] 10.2: Replace time.sleep with asyncio.sleep [SMALL]
- [ ] 10.3: Add exc_info=True to exception handling [SMALL]

---
## Phase 11: Critical Documentation Fixes [PENDING]
- [ ] 11.1: Update migration rollback docs [SMALL]

---
## Phase 12: Major Fixes - Provider Enum [PENDING]
- [ ] 12.1: Replace hardcoded provider enum with configurable mapping [MEDIUM]

---
## Phase 13: Major Fixes - Security [PENDING]
- [ ] 13.1: Fix weak CSP headers [SMALL]
- [ ] 13.2: Add webhook signature validation [MEDIUM]
- [ ] 13.3: Replace insecure randomness [SMALL]
- [ ] 13.4: Fix logging of sensitive data [SMALL]

---
## Phase 14: Major Fixes - Cross-Platform [PENDING]
- [ ] 14.1: Fix remaining shell=True [SMALL]
- [ ] 14.2: Fix hardcoded linux [SMALL]
- [ ] 14.3: Add Windows CLI docs [SMALL]

---
## Phase 15: Major Fixes - Documentation [PENDING]
- [ ] 15.1: Add deprecation timeline [SMALL]
- [ ] 15.2: Fix misleading TODOs [SMALL]
- [ ] 15.3: Implement Notion databases [MEDIUM]

---
## Phase 16: Major Fixes - Code Quality [PENDING]
- [ ] 16.1: Refactor boilerplate [MEDIUM]
- [ ] 16.2: Simplify wrappers [SMALL]
- [ ] 16.3: Deduplicate code [SMALL]

---
## Phase 17: Major Fixes - Tech Debt [PENDING]
- [ ] 17.1: Extract hardcoded config [MEDIUM]
- [ ] 17.2: Add auth tests [MEDIUM]
- [ ] 17.3: Add memory tests [MEDIUM]
- [ ] 17.4: Add search tests [MEDIUM]

---
## Phase 18: Major Fixes - Performance [PENDING]
- [ ] 18.1: Add type annotations [LARGE]
- [ ] 18.2: Add caching [MEDIUM]

---
## Phase 19: Feature Implementation [PENDING]
- [ ] 19.1: Implement query_images [MEDIUM]
- [ ] 19.2: Implement query_files [MEDIUM]
- [ ] 19.3: Implement relevant_memories [MEDIUM]
- [ ] 19.4: Configure operator agents [SMALL]

---
## Phase 20: Minor Enhancements [PENDING]
- [ ] 20.1: Fix remaining minor issues [SMALL]

---
## Phase 21: Critic Gate Review [PENDING]
- [ ] 21.1: Submit plan to Critic for final approval [MEDIUM]

---
## Phase 22: User Presentation [PENDING]
- [ ] 22.1: Present findings and plan to user [MEDIUM] (depends: 21.1)
