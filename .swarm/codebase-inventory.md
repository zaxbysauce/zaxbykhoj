# Codebase Inventory

## Tech Stack

### Core Languages
- **Python**: >=3.10, <3.13 (main backend, current versions: 3.10, 3.11, 3.12)
- **TypeScript**: Latest (web interfaces)
- **JavaScript**: ES6+ (desktop/obsidian interfaces)

### Frameworks
- **Backend Framework**:
  - **FastAPI** >= 0.110.0 (main web API)
  - **Django** 5.1.15 (admin panel, auth, models)
  - **Django-Unfold** 0.42.0 (admin interface)
  - **ASGI** (via uvicorn)

- **Frontend Frameworks**:
  - **React 18** (web interface)
  - **Next.js** (via Tauri desktop app)
  - **Obsidian API** (Obsidian plugin)
  - **Excalidraw** (diagram support)

- **AI/ML Frameworks**:
  - **PyTorch** 2.6.0 (ML operations)
  - **Transformers** >= 4.53.0 (HuggingFace models)
  - **Sentence-Transformers** 3.4.1 (embeddings)
  - **LangChain**:
    - `langchain-text-splitters` 0.3.11
    - `langchain-community` 0.3.31
  - **OpenAI** >= 2.0.0, < 3.0.0 (chat, embeddings)
  - **Anthropic** 0.75.0 (Claude API)
  - **Google GenAI** 1.52.0 (Gemini API)
  - **OpenAI Whisper** >= 20231117 (speech-to-text)
  - **Magika** ~= 0.5.1 (file type detection)

### Database
- **Primary Database**: PostgreSQL with pgvector 0.2.4 (vector embeddings)
- **Alternative**: SQLite with embedded pgserver 0.1.4 for local deployments
- **Vector Storage**: PostgreSQL pgvector extension
- **Full-Text Search**: PostgreSQL FTS5 (SearchVectorField)
- **Memory Storage**: Django ORM with vector fields

### Build System & Package Management
- **Python Build**: hatchling (pyproject.toml)
- **Python Linting**: ruff >= 0.12.0
- **Type Checking**: mypy >= 1.0.1
- **Testing**: pytest >= 7.1.2, pytest-django 4.5.2, pytest-asyncio 0.21.1
- **Frontend Build**:
  - Vite (React/Web interfaces)
  - Webpack (Obsidian plugin)
  - tauri (desktop app)

### Runtime Environment
- **Main**: Python 3.10+ with uvicorn >= 0.31.1
- **Web Browser**: Modern browsers with WebSockets 13.0+
- **Mobile**: Capacitor.JS (iOS/Android apps)
- **Desktop**: Electron/Qt (Python desktop app)

### Infrastructure & Integration
- **Containerization**: Docker with docker-compose
- **Message Queue**: APScheduler (background jobs)
- **Authentication**:
  - Session-based (Django)
  - OAuth (Google)
  - LDAP 2.9.1 (enterprise auth)
  - Phone number (Twilio)
- **Email**: resend 1.2.0, smtp
- **API Integrations**:
  - Web scrapers: Firecrawl, Olostep, Exa
  - Code execution: E2B code interpreter, Terrarium sandbox
  - Computer access: Docker-in-Docker computer

## File Inventory

### Source Files by Language
- **Python**: 242 files (main package)
  - Core application: 180+ files
  - Database models & migrations: 100+ migration files
- **TypeScript/TSX**: 76 files
  - React frontend: 54 files
  - Redesigned frontend: 22 files
- **JavaScript**: 13 files
  - Desktop interface
  - Obsidian plugin
  - Web client utilities

### Test Files
- **pytest**: 76 test files
- **Test Coverage**: Broad coverage across all core modules
- **Test Categories**:
  - Integration tests: test_rag_pipeline_e2e.py
  - Unit tests: test_*.py (74 files)
  - Benchmark tests: test_benchmark_*.py
  - LDAP tests: 8 test files
  - Migration tests: test_migration_*.py

### Configuration Files
- **Python**: pyproject.toml, pytest.ini, .pre-commit-config.yaml
- **Frontend**: package.json, tsconfig.json, vite.config.ts, tailwind.config.ts
- **Backend**: docker-compose.yml, gunicorn-config.py
- **Docker**: Dockerfiles for services
- **Linting**: ruff, mypy configurations

### Documentation Files
- **Markdown**: 78 files
- **MDX**: Advanced docs with embedded React components
- **Documentation Sections**:
  - Advanced features: 11 docs (LDAP, GCP, Ollama, etc.)
  - Client integration: 5 docs (Desktop, Emacs, Obsidian, Web, WhatsApp)
  - Contributing: 1 doc
  - Data sources: 3 docs (GitHub, Notion, Share)
  - Features: 13 docs (Agents, Automations, Chat, Image Gen, etc.)
  - Get Started: 3 docs (Overview, Privacy, Setup)
  - Miscellaneous: 7 docs (Credits, Performance, etc.)

## Architecture Overview

### Entry Points
1. **Main Application**: `khoj-repo/src/khoj/main.py`
   - CLI entry point (`khoj` command)
   - Server initialization
   - Django setup
   - Route configuration

2. **RAG Application**: `ragapp-repo/backend/app/main.py`
   - FastAPI backend
   - Independent service for RAG capabilities

### Module/Directory Structure

#### Main Khoj Package (khoj-repo/src/khoj/)

```
khoj/
├── app/                          # Django application configuration
│   ├── settings.py              # Django settings (279 lines)
│   ├── urls.py                  # URL routing
│   └── asgi.py                  # ASGI application
│
├── database/                     # Database layer
│   ├── models/                  # 944-line models.py
│   │   └── __init__.py          # Django models: User, Entry, Agent, Subscription, etc.
│   ├── adapters/                # Business logic adapters
│   │   └── __init__.py          # Data access layer
│   ├── migrations/              # 110+ migration files
│   │   └── manage.py
│   └── admin.py                 # Django admin configuration
│
├── processor/                    # Content processing
│   ├── content/                 # Document processors
│   │   ├── docx/                # DOCX parsing
│   │   ├── github/              # GitHub repo processing
│   │   ├── images/              # Image to text
│   │   ├── markdown/            # Markdown processing
│   │   ├── notion/              # Notion integration
│   │   ├── org_mode/            # Org-mode processing
│   │   ├── pdf/                 # PDF parsing
│   │   ├── plaintext/           # Plain text
│   │   ├── text_to_entries.py   # Generic text processor
│   │   └── __init__.py
│   ├── conversation/            # AI conversation
│   │   ├── anthropic/           # Claude chat
│   │   ├── google/              # Gemini chat
│   │   ├── openai/              # GPT chat
│   │   ├── prompts.py           # Conversation prompts
│   │   └── utils.py
│   ├── embeddings.py            # Vector embeddings (146 lines)
│   ├── query_transformer.py     # Query rephrasing
│   ├── retrieval_evaluator.py   # RAG quality evaluation
│   ├── sparse_embeddings.py     # Keyword search
│   ├── operator/                # Agent tools & computer access
│   │   ├── operator_agent_*.py
│   │   ├── operator_environment_*.py
│   │   └── grounding_agent.py
│   ├── speech/                  # Speech processing
│   │   └── text_to_speech.py
│   └── tools/                   # Agent tools
│       ├── mcp.py               # Model Context Protocol
│       ├── online_search.py
│       └── run_code.py
│
├── routers/                      # API endpoints (20 routers)
│   ├── api.py                   # Core API (268 lines)
│   ├── api_agents.py            # Agent management
│   ├── api_automation.py        # Automations
│   ├── api_chat.py              # Chat API
│   ├── api_content.py           # Content management
│   ├── api_memories.py          # Memory API
│   ├── api_metrics.py           # Telemetry
│   ├── api_model.py             # Model configuration
│   ├── api_phone.py             # Phone auth
│   ├── api_subscription.py      # Billing
│   ├── auth.py                  # Authentication
│   ├── email.py                 # Email utilities
│   ├── ldap.py                  # LDAP auth
│   ├── notion.py                # Notion sync
│   ├── research.py              # Research agent
│   ├── storage.py               # Storage management
│   ├── twilio.py                # Twilio integration
│   ├── web_client.py            # Web interface
│   └── helpers.py               # API helpers
│
├── search_type/                  # Search implementations
│   └── text_search.py           # Text search logic
│
├── search_filter/                # Search filters
│   ├── base_filter.py
│   ├── date_filter.py
│   ├── file_filter.py
│   └── word_filter.py
│
├── interface/                    # Client interfaces
│   ├── email/                   # Email client
│   ├── web/                     # React web interface (54 TSX/TS files)
│   │   ├── app/                 # Next.js app directory
│   │   │   ├── chat/            # Chat pages
│   │   │   ├── settings/        # Settings pages
│   │   │   ├── agents/          # Agent pages
│   │   │   ├── automations/     # Automation pages
│   │   │   ├── common/          # Shared components
│   │   │   ├── components/      # UI components (100+)
│   │   │   └── lib/             # Utilities
│   │   ├── components.json      # Shadcn/ui config
│   │   └── tailwind.config.ts
│   ├── desktop/                 # Tauri desktop app
│   ├── obsidian/                # Obsidian plugin (TypeScript)
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── api.ts
│   │   │   ├── chat_view.ts
│   │   │   └── settings.ts
│   │   └── package.json
│   └── android/                 # Capacitor mobile app
│
├── configure.py                  # Application configuration (551 lines)
├── main.py                       # Application entry point (258 lines)
├── utils/                        # Utilities (10 modules)
│   ├── cli.py                   # CLI parsing
│   ├── config.py                # Configuration helpers
│   ├── constants.py             # Constants
│   ├── helpers.py               # Helper functions
│   ├── initialization.py        # Initialization
│   ├── jsonl.py                 # JSONL utilities
│   ├── models.py                # Pydantic models
│   ├── rawconfig.py             # Config models (158 lines)
│   ├── secrets.py               # Secret management
│   ├── secrets_vault.py         # Vault-based secrets
│   ├── state.py                 # Global state
│   └── yaml.py                  # YAML utilities
│
└── telemtetry/                   # Telemetry tracking
    └── telemetry.py
```

#### RAG Application (ragapp-repo/)

```
ragapp-repo/
├── backend/                      # FastAPI backend (71 Python files)
│   ├── app/
│   │   ├── api/                 # REST API routes
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   ├── email.py
│   │   │   ├── health.py
│   │   │   ├── memories.py
│   │   │   ├── search.py
│   │   │   ├── settings.py
│   │   │   └── admin.py
│   │   ├── services/            # Business logic (13 services)
│   │   │   ├── chunking.py
│   │   │   ├── contextual_chunking.py
│   │   │   ├── document_processor.py
│   │   │   ├── email_service.py
│   │   │   ├── embeddings.py
│   │   │   ├── file_watcher.py
│   │   │   ├── llm_client.py
│   │   │   ├── memory_store.py
│   │   │   ├── query_transformer.py
│   │   │   ├── rag_engine.py
│   │   │   ├── reranking.py
│   │   │   ├── retrieval_evaluator.py
│   │   │   └── schema_parser.py
│   │   ├── middleware/          # HTTP middleware
│   │   ├── models/              # Database models
│   │   ├── config.py
│   │   ├── limiter.py
│   │   ├── main.py
│   │   ├── security.py
│   │   └── utils/
│   ├── tests/                   # Backend tests
│   ├── scripts/                 # Utility scripts
│   │   ├── backup_sqlite.py
│   │   ├── cleanup_backups.py
│   │   ├── migrate_memories.py
│   │   └── reset_embeddings.py
│   └── embedding_server/        # Optional embedding server
│
├── frontend/                     # React frontend (76 TSX/TS files)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── pages/               # React pages
│   │   │   ├── ChatPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── VaultsPage.tsx
│   │   │   ├── MemoryPage.tsx
│   │   │   └── LoginPage.tsx
│   │   ├── components/          # React components
│   │   │   ├── chat/            # Chat components
│   │   │   ├── shared/          # Shared components
│   │   │   ├── settings/        # Settings components
│   │   │   ├── ui/              # UI components
│   │   │   └── canvas/          # Canvas visualization
│   │   ├── contexts/            # React contexts
│   │   ├── hooks/               # Custom hooks
│   │   ├── lib/                 # Utilities
│   │   ├── stores/              # State management
│   │   ├── types/               # TypeScript types
│   │   └── test/                # Tests
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── redesign/                     # Redesigned frontend
│   └── frontend/                # New UI implementation
│
├── documentation/                # Documentation
│   ├── admin-guide.md
│   ├── email-ingestion.md
│   ├── release.md
│   └── non-technical-setup.md
│
└── README.md
```

### Dependency Graph

**Primary Dependencies**:
```
main.py
├── Django Framework
│   ├── Database Models (User, Entry, Agent, etc.)
│   ├── ORM (QuerySet, Migration system)
│   └── Admin Interface
│
├── FastAPI (Main API layer)
│   └── Routers (20 API endpoints)
│       ├── Authentication
│       ├── Content Management
│       ├── Chat & Conversations
│       ├── Agents & Automations
│       └── Memory System
│
├── Processor Layer
│   ├── Content Processors (8 formats)
│   │   ├── Text → Entries
│   │   ├── Images → Text
│   │   └── Web Sources → Entries
│   ├── Embeddings (Vector generation)
│   ├── Search (Hybrid + Full-text)
│   └── RAG Pipeline (Context retrieval)
│
├── AI Services
│   ├── LLM Providers (OpenAI, Anthropic, Google)
│   ├── Conversation Managers (Chat models)
│   ├── Speech (Whisper)
│   └── Vision (Image generation)
│
├── Database Storage
│   └── PostgreSQL + pgvector
│
└── External Integrations
    ├── LDAP (Enterprise auth)
    ├── Notion (Document sync)
    ├── GitHub (Repo processing)
    ├── Email (Outreach)
    ├── Twilio (SMS)
    └── Web Scrapers
```

### Plugin/Extension Points

1. **Content Sources**:
   - Document processors (DOCX, PDF, Markdown, Org-mode, Notion, GitHub)
   - Image processors (OCR, captioning)
   - Web scrapers (Firecrawl, Olostep, Exa)

2. **Agent Tools**:
   - Input tools: general, online, notes, webpage, code
   - Output modes: image, diagram
   - MCP (Model Context Protocol) servers

3. **Authentication**:
   - Session-based (Django)
   - OAuth providers (Google)
   - LDAP backend
   - Phone number (Twilio)

4. **Search Types**:
   - Hybrid search (sparse + dense + cross-encoder)
   - Full-text search (FTS5)
   - Vector search (pgvector)
   - Multi-scale chunking

5. **Frontend Extensions**:
   - React components (shadcn/ui + custom)
   - Obsidian plugin API
   - Desktop app hooks
   - Mobile app integrations

### State Management Approach

**Server State** (Global):
- `state` module in `utils/state.py`
- Server configuration
- Model instances (embeddings, cross-encoder)
- Process locks (distributed scheduler)
- Telemetry data

**User State**:
- Django ORM models per user
- Session storage
- Conversation history per user
- User preferences & settings

**Database**:
- PostgreSQL (primary)
- Models with vector fields (pgvector)
- Full-text search indexes
- Foreign key relationships

### External Service Integrations

**Core Services**:
1. **LLM Providers**:
   - OpenAI API (GPT models, embeddings)
   - Anthropic API (Claude models)
   - Google GenAI (Gemini models)

2. **Database Services**:
   - PostgreSQL with pgvector (vector search)
   - pgserver (embedded Postgres for local)

3. **Authentication**:
   - Google OAuth
   - LDAP 2.9.1 (enterprise)
   - Twilio (phone verification)
   - Resend (email)

4. **File Processing**:
   - Unstructured.io (document parsing)
   - PyMuPDF (PDF)
   - Magika (file type detection)
   - OpenAI Whisper (speech-to-text)

5. **Code Execution**:
   - E2B code interpreter
   - Terrarium sandbox
   - Operator environment (Docker-in-Docker)

6. **Web Services**:
   - Web scrapers (Firecrawl, Olostep, Exa)
   - SearxNG (search engine)
   - Notion API
   - GitHub API

7. **Monitoring & Telemetry**:
   - Sentry-like telemetry system
   - Usage metrics
   - Performance tracking

## Patterns Observed

### Coding Conventions

**Naming Conventions**:
- **Classes**: PascalCase (e.g., `EmbeddingsModel`, `ConversationAdapters`)
- **Functions**: snake_case (e.g., `execute_search`, `get_user_config`)
- **Variables**: snake_case (e.g., `query_embeddings`, `results`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `KHOJ_DOMAIN`, `DEFAULT_PORT`)
- **File Names**: snake_case (e.g., `text_to_entries.py`, `api_chat.py`)

**File Organization**:
- Modular by responsibility:
  - `processor/` - Content processing logic
  - `routers/` - API endpoints
  - `database/` - Data access
  - `utils/` - Shared utilities
  - `interface/` - Client implementations

- Consistent separation:
  - `app/` - Django app configuration
  - `models/` - Data models only
  - `adapters/` - Business logic + data access
  - `services/` - Domain-specific services

### Error Handling Patterns

1. **HTTP Exception**:
   ```python
   raise HTTPException(status_code=500, detail="Error message")
   ```

2. **Database Errors**:
   ```python
   except (DatabaseError, OperationalError):
       logger.error("DB Exception: Failed to authenticate user", exc_info=True)
       raise HTTPException(status_code=503, detail="Service temporarily unavailable")
   ```

3. **Retry with Tenacity**:
   ```python
   @retry(
       retry=retry_if_exception_type(requests.exceptions.HTTPError),
       wait=wait_random_exponential(multiplier=1, max=10),
       stop=stop_after_attempt(5),
   )
   def embed_with_hf(self, docs):
       # API call with retry logic
   ```

4. **Logging**:
   - Structured logging with `logging.getLogger(__name__)`
   - Rich logging with `RichHandler` for terminal
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - File handlers for persistent logs

### Logging/Observability Patterns

1. **Multi-Format Logging**:
   - Console: RichHandler with timestamps and traceback
   - File: FileHandler with DEBUG level
   - Module-level loggers with `__name__`

2. **Structured Telemetry**:
   - `update_telemetry_state()` helper
   - JSON serializable fields
   - Batched upload to telemetry server
   - Disabled via environment variable

3. **Process Locking**:
   - Distributed scheduler with leader election
   - `ProcessLock` model tracks operation locks
   - Prevents concurrent content indexing

4. **Database Connection Management**:
   - `AsyncCloseConnectionsMiddleware`
   - `close_old_connections()` calls
   - Connection pooling with Django

### Configuration Loading Patterns

1. **Environment Variables**:
   - `os.getenv("KHOJ_DOMAIN")` with defaults
   - Type checking via `is_env_var_true()`
   - Secret management via `secrets.py` or `secrets_vault.py`

2. **Pydantic Models**:
   - Config models in `rawconfig.py`
   - Type validation with aliases
   - Configuration helpers in `config.py`

3. **Django Settings**:
   - Settings defined in `app/settings.py`
   - Environment-specific overrides
   - Settings with fallbacks

4. **Dynamic Configuration**:
   - `SearchModelConfig` model for search models
   - Runtime model loading
   - Model config in database (not config files)

### Test Patterns

1. **Test Structure**:
   - Test files named `test_<module>.py`
   - Test modules in `tests/` directory
   - Separate standalone tests for isolation

2. **Test Categories**:
   - **Unit Tests**: Individual function/module tests
   - **Integration Tests**: API endpoint tests
   - **E2E Tests**: Full pipeline tests
   - **Benchmark Tests**: Performance tests
   - **LDAP Tests**: Security tests

3. **Test Fixtures**:
   - `conftest.py` for pytest fixtures
   - `conftest_minimal.py` for lightweight tests
   - Test data in `tests/data/`

4. **Test Markers**:
   ```python
   @pytest.mark.chatquality  # Quality evaluation tests
   ```

5. **Database Testing**:
   - `@pytest.mark.django_db` decorator
   - `--reuse-db` for performance
   - `freezegun` for time mocking

### API Design Patterns

1. **FastAPI Convention**:
   - Async functions (`async def`)
   - Pydantic request/response models
   - Dependency injection for auth/limits

2. **Authentication**:
   ```python
   @requires(["authenticated", "premium"])
   async def protected_endpoint(request: Request):
       # Protected route
   ```

3. **Rate Limiting**:
   ```python
   rate_limiter_per_minute = Depends(
       ApiUserRateLimiter(requests=20, subscribed_requests=100, window=60)
   )
   ```

4. **Streaming Responses**:
   - Server-Sent Events (SSE) for chat
   - Chunked responses for long operations

5. **Error Responses**:
   - HTTP 422 for validation errors
   - HTTP 503 for service errors
   - Detailed error messages in response body

### State Management Patterns

**Server-Side**:
- Global state object in `utils/state.py`
- Lazy initialization of components
- Process locks for distributed systems

**Client-Side (React)**:
- State management via React hooks
- Context providers for app-wide state
- Local stores for component isolation

**Database**:
- Django ORM with model-based state
- Database migrations for schema changes
- Foreign key relationships for data integrity

### Security Patterns

1. **Authentication**:
   - Session-based auth (Django)
   - Bearer token auth (API clients)
   - Phone number verification
   - LDAP authentication

2. **Secret Management**:
   - Environment variables for secrets
   - `secrets_vault.py` for encrypted storage
   - Never store credentials in code

3. **Input Validation**:
   - Pydantic models for request validation
   - Django model validation (`clean()`, `save()`)
   - Custom validators

4. **SQL Injection Prevention**:
   - Django ORM parameterized queries
   - No raw SQL except in migrations

5. **CSRF Protection**:
   - Django CSRF middleware
   - Trusted origins configuration

6. **HTTPS Enforcement**:
   - HTTPSRedirectMiddleware
   - Cookie security settings

### Deployment Patterns

1. **Docker Compose**:
   - Multi-service orchestration
   - Health checks
   - Volume mounting for persistence

2. **Process Management**:
   - Gunicorn for production (22.0.0)
   - Uvicorn for development
   - Background scheduler for tasks

3. **Scalability**:
   - Leader election for distributed tasks
   - Process locks for shared resources
   - Connection pooling

4. **Monitoring**:
   - Telemetry for usage tracking
   - Health check endpoints
   - Error logging

5. **Rollback Strategy**:
   - Database migrations with rollback support
   - Environment-specific configurations
   - Version tracking

### Documentation Patterns

1. **Docstrings**:
   - Google-style docstrings in Python
   - JSDoc in JavaScript
   - TypeScript comments for types

2. **Inline Documentation**:
   - Configuration comments in settings.py
   - Environment variable documentation
   - API endpoint documentation

3. **User Documentation**:
   - Markdown files in `documentation/`
   - MDX for interactive docs
   - Client-specific guides

4. **Developer Documentation**:
   - `README.md` for each module
   - Inline code comments
   - Architecture diagrams

### Code Quality Patterns

1. **Type Hints**:
   - Python type annotations throughout
   - Pydantic models for data validation
   - Generics for flexible typing

2. **Linting**:
   - Ruff for linting and formatting
   - mypy for type checking
   - Pre-commit hooks

3. **Code Organization**:
   - Single responsibility principle
   - Dependency injection
   - Separation of concerns

4. **Testing**:
   - 76 test files covering all modules
   - Integration and unit tests
   - Standalone tests for isolation

## Additional Notes

### Multi-Repository Structure
The codebase consists of two main repositories:
1. **khoj-repo**: Main Khoj application (primary focus)
2. **ragapp-repo**: Experimental RAG application (separate stack)

### Technology Diversity
- **Backend**: Python ecosystem (Django, FastAPI, PyTorch)
- **Frontend**: JavaScript ecosystem (React, TypeScript, Vite)
- **Database**: PostgreSQL + pgvector
- **Deployment**: Docker

### Key Characteristics
- **Modular Design**: Clear separation between concerns
- **Extensibility**: Plugin system for content sources, agents, tools
- **Multi-Client**: Desktop, Web, Obsidian, Mobile clients
- **Enterprise-Ready**: LDAP, Phone auth, RBAC
- **Production-Grade**: Error handling, logging, monitoring
- **Open Source**: AGPL-3.0 license

### Project Focus
- Personal knowledge management
- Semantic search with RAG
- Multi-format document indexing
- AI-powered conversation
- Agent system with tools
- Cross-platform accessibility
