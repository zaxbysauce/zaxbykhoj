# Khoj RAG Enhancement - Windows 11 Deployment Guide

**Repository:** https://github.com/zaxbysauce/zaxbykhoj  
**Phases:** 1-6 Complete (CRAG, Hybrid Search, Contextual Chunking, Multi-Scale, Migration Safety, Benchmark)  
**Platform:** Windows 11  
**Prerequisites:** OpenCode or similar LLM assistant

---

## 📋 Phase 0: Prerequisites Check

### Required Software (verify all installed):
```powershell
# Check Python (3.11+ required)
python --version

# Check Git
git --version

# Check PostgreSQL (14+ required)
psql --version

# Check Node.js (for frontend, optional)
node --version
```

### Required Environment Variables:
Create a `.env` file in the project root:
```env
# Database
KHOJ_DB_HOST=localhost
KHOJ_DB_PORT=5432
KHOJ_DB_NAME=khoj_db
KHOJ_DB_USER=khoj_user
KHOJ_DB_PASSWORD=your_secure_password

# OpenAI (for CRAG and contextual chunking)
OPENAI_API_KEY=sk-your-openai-key

# Optional: Gemini (for evaluation)
GEMINI_API_KEY=your-gemini-key
```

---

## 🗄️ Phase 1: Database Setup

### Step 1.1: Start PostgreSQL
```powershell
# If PostgreSQL installed as service
net start postgresql-x64-14

# Or use pgAdmin 4 to start server
```

### Step 1.2: Create Database and User
```powershell
# Open psql as postgres user
psql -U postgres

# In psql shell, run:
CREATE DATABASE khoj_db;
CREATE USER khoj_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE khoj_db TO khoj_user;
ALTER DATABASE khoj_db OWNER TO khoj_user;

# Enable pgvector extension (if not already enabled)
\c khoj_db
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

---

## 📥 Phase 2: Clone and Setup

### Step 2.1: Clone Repository
```powershell
# Navigate to your projects folder
cd C:\Users\%USERNAME%\Projects

# Clone the repository
git clone https://github.com/zaxbysauce/zaxbykhoj.git
cd zaxbykhoj\khoj-repo
```

### Step 2.2: Create Virtual Environment
```powershell
# Create venv
python -m venv .venv

# Activate venv
.venv\Scripts\activate

# Verify activation (should show (.venv) in prompt)
```

### Step 2.3: Install Dependencies
```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install core dependencies
pip install -e .

# Install additional RAG dependencies
pip install FlagEmbedding
pip install rank-bm25
pip install nltk

# Download NLTK data
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
```

---

## ⚙️ Phase 3: Configuration

### Step 3.1: Django Settings
Create or edit `src/khoj/app/.env`:
```env
DEBUG=True
SECRET_KEY=your-django-secret-key-here-change-in-production
DATABASE_URL=postgres://khoj_user:your_secure_password@localhost:5432/khoj_db
```

### Step 3.2: Verify Settings
```powershell
# Test Django settings
cd src
python -c "import django; django.setup(); print('Settings OK')"
```

---

## 🔄 Phase 4: Database Migrations

### Step 4.1: Run Migrations
```powershell
# From khoj-repo directory
cd src

# Run all migrations including RAG enhancements
python -m khoj manage migrate

# Verify migrations
python -m khoj manage showmigrations database
```

Expected output:
```
database
 [X] 0001_initial
 ...
 [X] 0099_alter...
 [X] 0100_add_search_vector      <-- Phase 2
 [X] 0101_add_context_summary    <-- Phase 3
 [X] 0102_add_chunk_scale        <-- Phase 4
```

### Step 4.2: Test Migration Reversibility
```powershell
# Test rollback (optional but recommended)
python -m khoj manage migrate database 0101
python -m khoj manage migrate database 0102

# Verify all migrations still apply cleanly
python -m khoj manage migrate
```

---

## 🧪 Phase 5: Run Tests

### Step 5.1: Run Core RAG Tests
```powershell
# From khoj-repo directory
cd tests

# Run Phase 4 tests (Multi-Scale Chunking)
pytest test_multi_scale_chunking.py -v

# Run Phase 5 tests (Migration Safety)
pytest test_rollback.py -v
pytest test_migration_reversibility.py -v
pytest test_migration_compatibility.py -v

# Run config tests
pytest test_rag_config.py -v
pytest test_rrf_fuse_multi.py -v
```

Expected: ~159 tests passing

### Step 5.2: Run Standalone Benchmark Tests
```powershell
# Test the benchmark script logic (no DB required)
python test_benchmark_standalone.py
```

Expected output:
```
======================================================================
ALL TESTS PASSED!
======================================================================
```

---

## 🚀 Phase 6: Start Khoj Server

### Step 6.1: Start the Server
```powershell
# From khoj-repo/src directory
python -m khoj
```

Server will start on `http://localhost:42110`

### Step 6.2: Verify Server Health
```powershell
# In new PowerShell window
curl http://localhost:42110/health
```

Expected: `{"status": "ok"}`

---

## 📊 Phase 7: Run Phase 6 Benchmark

### Step 7.1: Run Synthetic Dataset Benchmark
```powershell
# From khoj-repo directory
cd tests

# Run with synthetic dataset
python benchmark_retrieval.py `
  --dataset synthetic `
  --num-docs 100 `
  --num-queries 20 `
  --k 10 `
  --hybrid `
  --hybrid-alpha 0.6 `
  --output benchmark_synthetic_results.json
```

### Step 7.2: Alternative - Run with MS-MARCO (requires HuggingFace)
```powershell
# Install HuggingFace datasets if not already installed
pip install datasets

# Run with MS-MARCO mini
python benchmark_retrieval.py `
  --dataset msmarco_mini `
  --max-queries 100 `
  --hybrid `
  --output benchmark_msmarco_results.json
```

### Step 7.3: Interpret Results
The benchmark outputs a JSON file with metrics:
- **map_at_10**: Mean Average Precision @ 10 (PRIMARY METRIC)
- **ndcg_at_10**: Normalized DCG @ 10
- **recall_at_10/50/100**: Recall at different depths
- **mrr**: Mean Reciprocal Rank

**Decision Matrix:**
```
MAP@10 >= 0.95: SKIP Phase 6 - Current performance is excellent
MAP@10 0.90-0.95: OPTIONAL Phase 6 - Marginal gains expected
MAP@10 < 0.90: PROCEED with Phase 6 - Tri-vector may help significantly
```

---

## 🔍 Phase 8: Verify Features

### Step 8.1: Check Feature Flags
```powershell
# In Python interpreter
python -c "
from khoj.utils.config import RagConfig
print('CRAG Enabled:', RagConfig.crag_enabled)
print('Hybrid Search Enabled:', RagConfig.hybrid_search_enabled)
print('Multi-Scale Enabled:', RagConfig.multi_scale_chunking_enabled)
"
```

### Step 8.2: Test API Endpoints
```powershell
# Test RAG metrics endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" `
  http://localhost:42110/api/rag/metrics
```

Expected JSON with entry counts by scale and feature flags.

### Step 8.3: Test Multi-Scale Reindex (Dry Run)
```powershell
# From khoj-repo/src
python -m khoj manage reindex_multi_scale `
  --scales=512,1024,2048 `
  --dry-run
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'khoj'"
**Solution:**
```powershell
cd khoj-repo/src
python -m pip install -e ..
```

### Issue: "connection to server failed" (PostgreSQL)
**Solution:**
```powershell
# Check PostgreSQL service status
Get-Service -Name *postgres*

# Start if stopped
net start postgresql-x64-14

# Verify connection
psql -U khoj_user -d khoj_db -c "SELECT 1"
```

### Issue: "pgvector extension not found"
**Solution:**
```powershell
# Install pgvector for Windows
# Download from https://github.com/pgvector/pgvector/releases
# Or use conda:
conda install -c conda-forge pgvector
```

### Issue: OpenAI API errors
**Solution:**
```powershell
# Verify API key
$env:OPENAI_API_KEY

# Set if missing
$env:OPENAI_API_KEY="sk-your-key"
```

### Issue: Port 42110 already in use
**Solution:**
```powershell
# Find process using port
netstat -ano | findstr :42110

# Kill process (replace PID)
taskkill /PID <PID> /F
```

---

## 📁 Project Structure Reference

```
zaxbykhoj/
├── .swarm/                     # Project planning files
│   ├── plan.md                 # Implementation plan (35 tasks)
│   └── context.md              # Project context
├── khoj-repo/                  # Main Khoj source
│   ├── src/khoj/
│   │   ├── processor/          # RAG processors
│   │   │   ├── retrieval_evaluator.py    # Phase 1: CRAG
│   │   │   ├── query_transformer.py      # Phase 1: Query transformation
│   │   │   ├── sparse_embeddings.py      # Phase 2: Sparse vectors
│   │   │   ├── contextual_chunker.py     # Phase 3: Context summaries
│   │   │   └── embeddings.py
│   │   ├── search_type/
│   │   │   └── text_search.py  # Hybrid search, RRF fusion
│   │   ├── routers/
│   │   │   ├── api_chat.py     # Chat API with CRAG
│   │   │   └── api_metrics.py  # Phase 4: RAG metrics
│   │   ├── utils/
│   │   │   ├── config.py       # Phase 4: RagConfig
│   │   │   └── helpers.py      # RRF fusion functions
│   │   └── database/
│   │       ├── migrations/     # Phase 5: Reversible migrations
│   │       │   ├── 0100_add_search_vector.py
│   │       │   ├── 0101_add_context_summary.py
│   │       │   └── 0102_add_chunk_scale.py
│   │       └── management/
│   │           └── commands/
│   │               ├── populate_fts_index.py
│   │               └── reindex_multi_scale.py
│   └── tests/
│       ├── benchmark_retrieval.py      # Phase 6 benchmark
│       ├── test_multi_scale_chunking.py
│       ├── test_rollback.py
│       └── ...
└── HANDOFF.md                  # Complete handoff documentation
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] PostgreSQL running and accessible
- [ ] All migrations applied (0100, 0101, 0102)
- [ ] All migrations reversible (test rollback)
- [ ] Khoj server starts without errors
- [ ] Health endpoint responds
- [ ] All 159+ tests pass
- [ ] Benchmark runs successfully
- [ ] Feature flags accessible via RagConfig
- [ ] RAG metrics endpoint responds

---

## 📝 Notes for LLM Assistant

1. **File Paths:** Use Windows-style backslashes or raw strings in Python
2. **PowerShell:** Use backticks (`) for line continuation in commands
3. **Virtual Environment:** Always activate before running Python commands
4. **Environment Variables:** Set in PowerShell with `$env:VAR_NAME="value"`
5. **Database:** Ensure PostgreSQL service is running before migrations
6. **Testing:** Run standalone tests first (no DB), then full test suite
7. **Benchmark:** Requires running server and database

---

**End of Deployment Guide**

**Next Steps After Deployment:**
1. Run benchmark to establish baseline
2. If MAP@10 < 0.95, implement Phase 6 (Tri-Vector)
3. If MAP@10 >= 0.95, production deployment ready
