-- Retrieval performance indexes for RAG vector storage.
--
-- These indexes cover the concrete access paths used by the vector store:
-- source inspection ordered by chunk_index, model-filtered semantic search,
-- and embedding freshness/debug queries by model.

CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_chunk_index
    ON rag_chunks(source_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_rag_embeddings_model_embedded_at
    ON rag_embeddings(embedding_model, embedded_at DESC);
