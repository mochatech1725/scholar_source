-- Enforce one stored embedding per normalized chunk content hash and model.
-- The embedder skips existing hashes before provider calls; this unique index
-- protects repeated runs and concurrent writers from creating duplicates.

CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_embeddings_content_model_unique
    ON rag_embeddings(content_hash, embedding_model);
