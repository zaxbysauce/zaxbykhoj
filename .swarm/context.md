# Context
Swarm: paid

## Handoff Status
**Date:** 2026-03-07  
**Status:** Phases 1-5 COMPLETE ✅ | Phase 6 PENDING EVALUATION  
**Handoff Document:** `C:/opencode/khoj/HANDOFF.md`

**Summary:**
- 35/35 core tasks completed across Phases 1-5
- 159+ tests passing
- All migrations reversible with rollback documentation
- Production-ready with full QA discipline maintained

**Key Deliverables:**
- Phase 1-3: CRAG, Query Transformation, Hybrid Search, Contextual Chunking
- Phase 4: Multi-Scale Chunking (512/1024/2048), RagConfig, `/api/rag/metrics`, `reindex_multi_scale` command
- Phase 5: Reversible migrations, rollback docs, 65 migration/compatibility/rollback tests

**Next Steps:**
1. Review handoff at HANDOFF.md
2. Verify state: `python manage.py showmigrations database`
3. Run tests: `pytest tests/test_rollback.py -v`
4. Phase 6 Decision: Evaluate if tri-vector support needed (benchmark first)

---

## Project Overview

This project enhances Khoj's RAG (Retrieval-Augmented Generation) system by importing advanced techniques from the ragapp repository. The goal is to improve retrieval accuracy, reduce hallucinations, and provide better context for LLM generation.

## Source Code Locations

### Khoj (target for modifications)
- Embeddings: `khoj-repo/src/khoj/processor/embeddings.py`
- Search/Retrieval: `khoj-repo/src/khoj/search_type/text_search.py`
- Content Processing: `khoj-repo/src/khoj/processor/content/text_to_entries.py`
- Chat API: `khoj-repo/src/khoj/routers/api_chat.py`
- Prompts: `khoj-repo/src/khoj/processor/conversation/prompts.py`
- Database Models: `khoj-repo/src/khoj/database/models/__init__.py`
- **RagConfig:** `khoj-repo/src/khoj/utils/config.py` ⭐ NEW
- **Metrics API:** `khoj-repo/src/khoj/routers/api_metrics.py` ⭐ NEW
- **Multi-Scale Command:** `khoj-repo/src/khoj/database/management/commands/reindex_multi_scale.py` ⭐ NEW

### ragapp (reference implementation)
- Embeddings: `ragapp-repo/backend/app/services/embeddings.py`
- RAG Engine: `ragapp-repo/backend/app/services/rag_engine.py`
- Contextual Chunking: `ragapp-repo/backend/app/services/contextual_chunking.py`
- Reranking: `ragapp-repo/backend/app/services/reranking.py`
- Fusion: `ragapp-repo/backend/app/utils/fusion.py`
- Query Transformer: `ragapp-repo/backend/app/services/query_transformer.py`
- Retrieval Evaluator: `ragapp-repo/backend/app/services/retrieval_evaluator.py`

## SME Cache

### Hybrid Search Architecture
- **Approach**: PostgreSQL FTS + pgvector with RRF fusion
- **Sparse storage**: tsvector column with GIN index, or sparse vector as JSONB
- **Model**: BGE-M3 or SPLADE-v3 for sparse embeddings
- **Fusion**: RRF with k=60 is robust to score scale differences
- **Multi-tenant**: Partition by tenant_id or use partial indexes
- **Index choice**: HNSW for >10k vectors (better recall-speed), IVFFlat for limited RAM

### Tri-Vector Embeddings
- **Model**: BAAI/bge-m3 outputs dense, sparse, and colbert in single forward pass
- **Storage impact**: ColBERT stores matrix per passage (~20GB for 10M passages vs 0.8GB dense-only)
- **Compute impact**: ~10x query cost for ColBERT MaxSim vs dense
- **Recommendation**: Dense+sparse may be sufficient; ColBERT adds 2-5% nDCG at 2-3x storage cost
- **Fusion weights**: 0.4 dense, 0.2 sparse, 0.4 colbert (tune on validation set)
- **Phase 6 Gate**: Only proceed if Phase 1-5 baseline shows MAP@10 gain < 0.05

### CRAG Evaluation
- **Classes**: CONFIDENT (proceed), AMBIGUOUS (expand search), NO_MATCH (pure LLM/clarify)
- **Model**: Use smaller/faster model (gpt-4o-mini, Claude haiku) - 2-3x cheaper
- **Latency**: ~150-250ms per evaluation; use dynamic gating (skip if similarity > 0.75)
- **Prompt**: System defines task, user provides query + top-3 truncated chunks (500 chars each)
- **Improvement**: ~10-15% precision gain on MS-MARCO benchmarks

### Query Transformation
- **Techniques**: Step-back prompting (good for abstract), Multi-query (highest recall), HyDE (excellent for factual Q&A)
- **Recommended**: Hybrid approach - rule-based synonyms + 1-2 LLM variants
- **Variant count**: 3 total (1 rule + 2 LLM) for ~10-15% recall gain, ~250ms latency
- **Fusion**: RRF with k=60 for combining variant results
- **Disable when**: Single-token identifiers, code symbols, latency-critical UI

### Contextual Chunking
- **Improvement**: +10-20% MRR/Recall on benchmarks, most pronounced for long heterogeneous docs
- **Approach**: LLM generates 1-2 sentence context per chunk (30-45 tokens)
- **Storage**: Store as separate metadata field (context_summary), NOT prepended to chunk
- **Cost**: ~$0.018 per 10k-token doc (40 chunks x 30 tokens @ gpt-4o-mini rates)
- **Prompt**: System enforces brevity, temperature=0 for determinism

### pgvector Optimization
- **Index**: HNSW with m=16, ef_construction=200 for production
- **Hybrid search**: Add tsvector column with GIN index, weighted score combination
- **Multi-tenant**: Partition by tenant_id, local HNSW indexes per partition
- **Scaling limit**: ~20-30M vectors on 64GB instance for sub-second queries
- **Variable dimensions**: Not supported - use separate tables per dimension

## Patterns

### RRF (Reciprocal Rank Fusion)
```
score = sum(1 / (k + rank)) for each result list
k = 60 (standard)
```
- Deduplicates by ID, accumulates scores
- Robust to score scale differences

### CRAG Pipeline
```
1. Retrieve top-N documents
2. LLM evaluates: query + top-3 chunks -> CONFIDENT/AMBIGUOUS/NO_MATCH
3. Branch based on classification:
   - CONFIDENT: proceed with generation
   - AMBIGUOUS: expand search, re-rank
   - NO_MATCH: pure LLM or user clarification
```

### Hybrid Search Pipeline
```
1. Dense: pgvector cosine distance search
2. Sparse: PostgreSQL FTS ts_rank_cd
3. Fusion: weighted sum (0.6 dense + 0.4 sparse) or RRF
```

### Multi-Scale Chunking Pipeline
```
1. Create chunks at multiple sizes (512, 1024, 2048 tokens)
2. Store with chunk_scale field ('512', '1024', '2048', 'default')
3. Search across all scales
4. Fuse results with rrf_fuse_multi()
```

## Decisions (Confirmed)

- **Phase 6 (Tri-Vector)**: Marked as OPTIONAL - will evaluate necessity based on Phase 1-5 metrics. Gate condition: MAP@10 gain < 0.05
- **Phase 5 (Migration Safety)**: ✅ COMPLETE - All migrations reversible with full rollback documentation
- **CRAG Model**: Use smaller model (gpt-4o-mini equivalent) for evaluation to minimize latency/cost
- **Contextual Chunking**: Store context separately, not prepended, to enable hybrid retrieval
- **Multi-Scale**: Default sizes 512, 1024, 2048 tokens (configurable via RagConfig)

## Configuration Toggles (Implemented in RagConfig)

| Feature | Config Flag | Default | Status |
|---------|-------------|---------|--------|
| CRAG Evaluation | `crag_enabled` | true | ✅ Implemented |
| Query Transformation | `query_transform_enabled` | true | ✅ Implemented |
| Hybrid Search | `hybrid_search_enabled` | true | ✅ Implemented |
| Contextual Chunking | `contextual_chunking_enabled` | false | ✅ Implemented |
| Multi-Scale Chunking | `multi_scale_chunking_enabled` | false | ✅ Implemented |
| Tri-Vector Search | `tri_vector_search_enabled` | false | ✅ Implemented |

## Dependencies Added

- `FlagEmbedding` (BGE-M3 for sparse/colbert) - Phase 2
- `nltk` (WordNet for query expansion) - Phase 1
- `rank_bm25` (optional, for lexical re-ranking) - Phase 2

## Migration Safety

All RAG enhancement migrations are explicitly reversible:
- `0100_add_search_vector` → reverses to RemoveField + RemoveIndex
- `0101_add_context_summary` → reverses to RemoveField  
- `0102_add_chunk_scale` → reverses to RemoveField

**Rollback Documentation:** `docs/migration_rollback.md`

## Critical Lessons Learned

### ⚠️ QA GATE DISCIPLINE - MANDATORY

**CORRECT PROCESS (Enforced throughout Phases 1-5):**
```
Task N:
  ↓
[Coder implements] 
  ↓
[Stage A: pre_check_batch] → FAIL → [Fix] → [Re-run]
  ↓ PASS
[Stage B: Reviewer] → REJECTED → [Fix] → [Re-run]
  ↓ APPROVED
[Stage B: Test Engineer] → FAIL → [Fix] → [Re-run]
  ↓ PASS
[Mark Task N complete]
  ↓
[Proceed to Task N+1]
```

**RULE:** NO task may be marked complete until ALL Stage A and Stage B gates pass. NO exceptions.

**ENFORCEMENT:** This workflow was hard-coded throughout Phases 1-5. Zero batching violations.

---

## Project Governance

Standard Khoj contribution guidelines apply:
- Code must pass lint checks
- Tests required for new functionality
- Django migrations must include reverse operations
- **ALL changes MUST go through complete QA gates before marking tasks complete**

## Agent Activity

| Tool | Calls | Success | Failed | Avg Duration |
|------|-------|---------|--------|--------------|
| read | 1644 | 1644 | 0 | 7ms |
| bash | 1214 | 1214 | 0 | 1012ms |
| edit | 510 | 510 | 0 | 2458ms |
| task | 344 | 344 | 0 | 110040ms |
| grep | 335 | 335 | 0 | 112ms |
| glob | 226 | 226 | 0 | 25ms |
| retrieve_summary | 127 | 127 | 0 | 3ms |
| write | 103 | 103 | 0 | 3717ms |
| todowrite | 68 | 68 | 0 | 4ms |
| pre_check_batch | 68 | 68 | 0 | 2902ms |
| lint | 60 | 60 | 0 | 2852ms |
| test_runner | 45 | 45 | 0 | 17782ms |
| update_task_status | 44 | 44 | 0 | 6ms |
| diff | 21 | 21 | 0 | 12ms |
| phase_complete | 19 | 19 | 0 | 5ms |
| save_plan | 12 | 12 | 0 | 6ms |
| imports | 11 | 11 | 0 | 4ms |
| evidence_check | 4 | 4 | 0 | 2ms |
| invalid | 4 | 4 | 0 | 1ms |
| write_retro | 4 | 4 | 0 | 5ms |
| todo_extract | 2 | 2 | 0 | 2ms |
| apply_patch | 2 | 2 | 0 | 113ms |
| secretscan | 2 | 2 | 0 | 135ms |
| webfetch | 2 | 2 | 0 | 316ms |
| mystatus | 1 | 1 | 0 | 2165ms |
| checkpoint | 1 | 1 | 0 | 7ms |
