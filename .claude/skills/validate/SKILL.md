---
name: validate
description: Run ScholarSource validation gates after implementing any feature or fix. Invoke before marking any task complete.
---

# Validate

Run in order. All must pass before marking work complete.

## Backend

```bash
ruff check .
ruff format --check .
pytest tests/ -x
```

## Frontend

```bash
cd web && npm run lint
cd web && npm run test:run
```

## RAG Pipeline Checklist

Before marking any pipeline module complete, verify:

- [ ] Every chunk carries: source_id, url, title, content_hash, embedding_model
- [ ] Every submitted query produces a run log entry before the pipeline returns
- [ ] No LLM synthesis call is made when retrieved chunks are empty
- [ ] Source URLs are verified before storage
- [ ] Retrieved evidence and model synthesis are explicitly separated in all responses
- [ ] Sources rejected by quality checks have a logged accept/reject reason
