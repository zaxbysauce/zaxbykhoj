<!-- PLAN_HASH: 20ozep4swqoan -->
# Khoj RAG Enhancement - Hybrid Search, CRAG, Query Transformation
Swarm: paid
Phase: 6 [PENDING] | Updated: 2026-03-07

---
## Phase 1: CRAG Evaluation & Query Transformation [COMPLETE]
- [x] 1.1: Create RetrievalEvaluator class in processor/retrieval_evaluator.py with evaluate(query, chunks) returning CONFIDENT/AMBIGUOUS/NO_MATCH using gpt-4o-mini [MEDIUM]
- [x] 1.2: Implement fallback in retrieval_evaluator.py: CONFIDENT->return chunks, AMBIGUOUS->lower threshold and re-search, NO_MATCH->return empty with warning [MEDIUM] (depends: 1.1)
- [x] 1.3: Create QueryTransformer class in processor/query_transformer.py with transform(query) returning [original, step_back] using gpt-4o-mini [MEDIUM]
- [x] 1.4: Create rrf_fuse(results_lists, k=60, limit=10) function in utils/helpers.py returning sorted Entry list [SMALL]
- [x] 1.5: Add import for RetrievalEvaluator in routers/api_chat.py [SMALL] (depends: 1.1)
- [x] 1.6: Add CRAG evaluation logic after vector search in api_chat.py when enabled [SMALL] (depends: 1.5)
- [x] 1.7: Add query transformation before embedding generation in api_chat.py when enabled [SMALL] (depends: 1.3)
- [x] 1.8: Add RRF fusion for query variants in api_chat.py when multiple variants exist [SMALL] (depends: 1.4, 1.7)
- [x] 1.9: Create tests/test_retrieval_evaluator.py and tests/test_query_transformer.py with mock LLM responses [MEDIUM] (depends: 1.6, 1.8)
- [x] 1.10: Add test_confident_fallback(), test_ambiguous_fallback(), test_no_match_fallback() to test_retrieval_evaluator.py [SMALL] (depends: 1.9)

---
## Phase 2: Hybrid Search - Dense + Sparse/BM25 [COMPLETE]
- [x] 2.1: Create Django migration 0100_add_search_vector: AddField('Entry', 'search_vector', TSVectorField()), AddIndex(GinIndex(fields=['search_vector'])) [SMALL]
- [x] 2.2: Create SparseEmbeddingGenerator in processor/sparse_embeddings.py using FlagEmbedding BGEM3FlagModel for lexical weights [MEDIUM]
- [x] 2.3: Refactor existing vector search into dense_search(query_embedding, user, k=10) in search_type/text_search.py [SMALL]
- [x] 2.4: Create sparse_search(query_text, user, k=10) using Entry.objects.annotate(rank=SearchRank('search_vector')) in text_search.py [SMALL]
- [x] 2.5: Create hybrid_search(query_text, query_embedding, user, k=10, alpha=0.6) calling dense_search and sparse_search, then rrf_fuse [MEDIUM]
- [x] 2.6: Add hybrid_alpha=FloatField(default=0.6) and hybrid_enabled=BooleanField(default=True) to database/models/SearchModelConfig [SMALL]
- [x] 2.7: Create management command: python manage.py populate_fts_index --batch-size=1000 [MEDIUM]
- [x] 2.8: Create tests/test_hybrid_search.py with parameterized tests for alpha=0.3, 0.5, 0.7 [MEDIUM]

---
## Phase 3: Contextual Chunking & Window Expansion [COMPLETE]
- [x] 3.1: Create Django migration 0101_add_context_summary: AddField('Entry', 'context_summary', models.TextField(blank=True, null=True)) [SMALL]
- [x] 3.2: Create ContextualChunker class in processor/contextual_chunker.py using gpt-4o-mini, temperature=0, max_tokens=60 [MEDIUM]
- [x] 3.3: Add chunker.summarize_chunk() call in processor/content/markdown/markdown_to_entries.py when flag enabled [SMALL]
- [x] 3.4: Add chunker.summarize_chunk() call in processor/content/pdf/pdf_to_entries.py when flag enabled [SMALL]
- [x] 3.5: Add chunker.summarize_chunk() call in processor/content/org_mode/org_to_entries.py when flag enabled [SMALL]
- [x] 3.6: Create expand_window(entry, window_size=2) in search_type/text_search.py fetching adjacent chunks [MEDIUM]
- [x] 3.7: Update processor/conversation/prompts.py to prepend entry.context_summary to reference text when available [SMALL]
- [x] 3.8: Create tests/test_contextual_chunker.py with mock LLM, rate limit (5 concurrent), error handling tests [SMALL]

---
## Phase 4: Multi-Scale Chunking & Configuration [COMPLETE]
- [x] 4.1: Create Django migration 0102_add_chunk_scale: AddField('Entry', 'chunk_scale', models.CharField(max_length=16, default='default')) [SMALL]
- [x] 4.2: Modify processor/content/text_to_entries.py to create entries at multiple chunk_size values [MEDIUM]
- [x] 4.3: Create rrf_fuse_multi(sources: Dict[str, List[Result]], k=60, limit=10) in utils/helpers.py [MEDIUM]
- [x] 4.4: Add RagConfig class to utils/config.py with feature flags for all RAG enhancements [SMALL]
- [x] 4.5: Create routers/api_metrics.py with /api/rag/metrics endpoint [MEDIUM]
- [x] 4.6: Create management command: python manage.py reindex_multi_scale --scales=512,1024,2048 --dry-run [MEDIUM]
- [x] 4.7: Create comprehensive tests: test_multi_scale_chunking.py, test_rrf_fuse_multi.py, test_rag_config.py, test_api_metrics.py, test_reindex_multi_scale.py [MEDIUM]

---
## Phase 5: Schema Migration Safety & Rollback [COMPLETE]
- [x] 5.1: Add ReverseMigration operations to migrations 0100, 0101, 0102 making all migrations explicitly reversible [MEDIUM]
- [x] 5.2: Create docs/migration_rollback.md with rollback steps: pg_dump, apply reverse migration, verify row count, verify query results [SMALL]
- [x] 5.3: Create tests/test_migration_compatibility.py verifying: Entry.objects.filter(user=user), search_with_embeddings(), FTS search, agent isolation [MEDIUM]
- [x] 5.4: Create tests/test_rollback.py that applies migration, inserts test entries, runs reverse migration, verifies columns removed and row count preserved [SMALL]

---
## Phase 6: Optional Tri-Vector Support (Dense + Sparse + Colbert) [PENDING EVALUATION]
- [ ] 6.1: Evaluate tri-vector by running benchmarks against Phase 1-5 baseline - ONLY PROCEED if MAP@10 gain < 0.05 [SMALL]
- [ ] 6.2: If approved: Add TriVectorEmbeddingGenerator in processor/tri_vector_embeddings.py using FlagEmbedding BGEM3FlagModel [LARGE] (depends: 6.1)
- [ ] 6.3: If approved: Create migration AddField('Entry', 'colbert_vector', models.BinaryField(blank=True, null=True)) [MEDIUM] (depends: 6.2)
- [ ] 6.4: If approved: Create tri_vector_search() in text_search.py computing weighted sum of normalized scores [LARGE] (depends: 6.3)
