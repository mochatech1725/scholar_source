# Audit Fixes

Legend: `[ ]` = pending · `[x]` = complete

---

## Security — High Priority

- [X] **1. Remove raw user inputs from logs** (`tasks.py:93, 253, 271, 353, 521, 539`)
  Replace `logger.info(f"Job {job_id} parameters: {inputs}")` with log lines that record only `job_id` and field names, never values.

- [x] **2. Strip stack traces from API responses** (`tasks.py:289-292, 556-560`)
  Remove `metadata["stack_trace"]` from the dict stored in the DB and returned to the client. Keep stack traces server-side in logs only.

- [x] **3. Block `javascript:` URLs in resource links** (`ResultCard.jsx:146-153`)
  Before rendering `<a href={resource.url}>`, validate the protocol is `http://` or `https://`. Silently omit or disable the link if invalid.

- [x] **4. Fix empty URL scheme in `security_utils.py`** (`security_utils.py:95-102`)
  Remove `''` from the allowed schemes list so protocol-relative URLs like `//evil.com` are rejected. Only `http` and `https` should be accepted.

- [x] **5. Restrict CORS `allow_headers` to an explicit list** (`main.py:84`)
  Replace `allow_headers=["*"]` with an explicit list: `["Authorization", "Content-Type", "X-CSRF-Token"]`.

- [x] **6. Guard missing `VITE_API_URL` in production** (`web/src/lib/supabase.js`)
  Add a check so the app throws a clear error at startup if `VITE_API_URL` is absent in a production build instead of silently falling back to `localhost:8000`.

---

## Security — Lower Priority

- [x] **7. Add client-side file size + MIME type check on PDF upload** (`HomePage.jsx:407-418`)
  Before sending the file to the backend, validate `file.type === 'application/pdf'` and `file.size <= 50 * 1024 * 1024`. Show an inline error if either check fails.

- [x] **8. Validate `job_id` as UUID type in FastAPI route** (`main.py:295`)
  Change the `job_id: str` parameter to `job_id: UUID` so FastAPI rejects malformed IDs at the framework level before any DB query runs.

- [x] **9. Control `localhost` CORS origins via environment variable** (`main.py:74-76`)
  Move hardcoded `http://localhost:*` origins into an env var so they are absent in production builds.

- [x] **10. Replace Referer with Origin-only CSRF validation** (`csrf_protection.py:50-83`)
  The Referer header can be stripped or spoofed. Rely solely on the `Origin` header for CSRF validation; keep Referer only as a fallback log note.

---

## Duplicate Code

- [x] **11. Extract `getSiteName()` to a shared utility** (`ResultCard.jsx:41-88`, `ResultsTable.jsx:33-52`)
  Create `web/src/lib/resourceUtils.js`, export one `getSiteName(url)` function, and import it in both components.

- [x] **12. Unify type-badge / resource-meta mapping** (`ResultCard.jsx:23-31`, `ResultsTable.jsx:12-31`)
  The `TYPE_META` object in `ResultsTable` is the better implementation. Move it to `resourceUtils.js` and remove the duplicate `getBadgeClass()` logic in `ResultCard`.

- [x] **13. Extract clipboard copy to a `useCopyToClipboard` hook** (`ResultCard.jsx:12-21`, `ResultsTable.jsx:59-68`)
  Identical `copied` state + 2-second timeout logic. Create `web/src/hooks/useCopyToClipboard.js` and replace both usages.

- [x] **14. Extract shared auth form input component** (`LoginForm.jsx:51-94`, `SignupForm.jsx:74-145`)
  The styled email/password inputs are copy-pasted 5+ times. Create a `web/src/components/Auth/AuthInput.jsx` primitive and replace all occurrences.

- [x] **15. Extract shared helpers from `run_crew_task` / `run_crew_task_sync`** (`tasks.py`)
  The two Celery task functions are ~85% identical. Extract: input normalization, prompt injection validation, crew execution, result parsing, error handling, and PDF cleanup into private helper functions called by both.

- [x] **16. Extract job authorization check into a helper** (`main.py:330-338`, `main.py:419-427`)
  The "does this job belong to the current user" guard is copy-pasted in `get_job_status` and `cancel_job`. Extract to a `verify_job_ownership(job, user_id)` helper.

---

## React / FastAPI Best Practices

- [x] **17. Add an Error Boundary to `App.jsx`**
  Wrap the route tree in an Error Boundary component so an unhandled render crash shows a graceful fallback instead of a blank screen.

- [x] **18. Fix auth state race condition in `AuthContext.jsx`** (`AuthContext.jsx:27-36`)
  `getSession()` and `onAuthStateChange` can resolve in conflicting order. Use the `onAuthStateChange` event stream as the single source of truth and drop the separate `getSession()` call.

- [x] **19. Fix array index fallback key in `ResultsTable`** (`ResultsTable.jsx:322`)
  Replace `resource-${index}` fallback with a deterministic key (e.g. a hash of `resource.title + resource.url`) so React reconciliation is stable even when URLs are missing.

- [x] **20. Stabilize `InlineSearchStatus` polling effect** (`InlineSearchStatus.jsx:151`)
  Move the timeout flag to a `useRef` so it doesn't appear in the effect dependency array. This prevents the polling interval from being torn down and restarted unnecessarily.

- [x] **21. Clear selection state on `handleReset()`** (`HomePage.jsx:117-139`)
  `selectionState.selectedCount` is not reset when the user clears the form, leaving the action bar in a stale state. Add the reset call.

- [x] **22. Fix duplicate `import os` in `main.py`** (`main.py:8` and `main.py:30`)
  Remove the second `import os` statement.

- [x] **23. Replace broad `except Exception` with specific exceptions** (`main.py:145, 277`, `tasks.py:102`)
  Catch `ConnectionError`, `TimeoutError`, `HTTPException`, etc. specifically so unexpected errors (MemoryError, KeyboardInterrupt) are not silently swallowed.

- [x] **24. Validate `desired_resource_types` list items** (`tasks.py:115-117`)
  After confirming the field is a list, check that each item is a member of the allowed resource type enum. Discard or error on unrecognised values.

- [x] **25. Declare `warning` field in `JobSubmitResponse`** (`models.py:178-192`)
  The `submit_job` endpoint conditionally adds a `warning` key to the response but the Pydantic model doesn't declare it. Add `warning: Optional[str] = None`.

- [x] **26. Log PDF cleanup failures** (`tasks.py:229-232, 494-500`)
  Replace `except Exception: pass` with `except Exception as e: logger.warning(f"Failed to remove temp PDF {pdf_path}: {e}")`.
