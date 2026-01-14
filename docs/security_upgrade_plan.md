# Security Fixes Implementation Plan - ScholarSource

## Overview
Comprehensive security improvements to address vulnerabilities found in the security audit, implementing authentication, input validation, prompt injection detection, HTML escaping, and dependency management.

## User Preferences (from Q&A)
- **Authentication:** Email/Password only with Supabase Auth
- **Cache Scope:** User-specific (private per user)
- **Prompt Injection:** Strict blocking mode (reject suspicious inputs)
- **Migration:** Start fresh - require authentication for all access

---

## Phase 1: Database Schema & Authentication Foundation

### [✅] 1.1 Update Database Schema (supabase_schema.sql)

**File:** `supabase_schema.sql`

**Changes:**
1. Add `user_id` column to `jobs` table:
   ```sql
   ALTER TABLE jobs ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
   ALTER TABLE jobs ALTER COLUMN user_id SET NOT NULL;
   ```

2. Add `user_id` column to `course_cache` table:
   ```sql
   ALTER TABLE course_cache ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
   ALTER TABLE course_cache ALTER COLUMN user_id SET NOT NULL;
   ```

3. Update `jobs` RLS policies:
   ```sql
   -- Remove old permissive policy
   DROP POLICY IF EXISTS "Enable all access for jobs" ON jobs;

   -- Add user-scoped policies
   CREATE POLICY "Users can view own jobs" ON jobs
       FOR SELECT USING (auth.uid() = user_id);

   CREATE POLICY "Users can create own jobs" ON jobs
       FOR INSERT WITH CHECK (auth.uid() = user_id);

   CREATE POLICY "Users can update own jobs" ON jobs
       FOR UPDATE USING (auth.uid() = user_id);

   CREATE POLICY "Users can delete own jobs" ON jobs
       FOR DELETE USING (auth.uid() = user_id);
   ```

4. Update `course_cache` RLS policies (same pattern):
   ```sql
   DROP POLICY IF EXISTS "Enable all access for course_cache" ON course_cache;

   CREATE POLICY "Users can view own cache" ON course_cache
       FOR SELECT USING (auth.uid() = user_id);

   CREATE POLICY "Users can create own cache" ON course_cache
       FOR INSERT WITH CHECK (auth.uid() = user_id);

   CREATE POLICY "Users can update own cache" ON course_cache
       FOR UPDATE USING (auth.uid() = user_id);

   CREATE POLICY "Users can delete own cache" ON course_cache
       FOR DELETE USING (auth.uid() = user_id);
   ```

5. Create migration script to delete existing anonymous jobs:
   ```sql
   -- Clean slate for authentication
   TRUNCATE jobs CASCADE;
   TRUNCATE course_cache CASCADE;
   ```

### [✅] 1.2 Create Authentication Middleware (backend/auth.py)

**New file:** `backend/auth.py`

**Purpose:** Verify Supabase JWT tokens and extract user context

**Key components:**
1. `verify_jwt_token(token: str)` - Verify JWT signature using Supabase JWT secret
2. `get_current_user(request: Request)` - FastAPI dependency to extract user from Authorization header
3. `get_user_id_from_token(token: str)` - Extract user_id from verified JWT
4. Custom exception `AuthenticationError` for 401 responses

**Implementation approach:**
- Use PyJWT library to verify tokens
- Extract JWT secret from Supabase environment
- Return 401 Unauthorized for missing/invalid tokens
- Store user_id in request.state for endpoint access

### [✅] 1.3 Update Backend Dependencies (requirements.txt, pyproject.toml)

**Files:** `requirements.txt`, `pyproject.toml`

**Add new dependencies:**
```
PyJWT>=2.8.0,<3.0.0           # JWT token verification
cryptography>=41.0.0,<42.0.0  # Required by PyJWT for RS256
```

**Pin all existing dependencies** to specific minor versions:
```
crewai[tools]==0.120.1
lancedb==0.25.0
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
pydantic[email]==2.0.0
supabase==2.0.0
python-dotenv==1.0.0
resend==0.8.0
slowapi==0.1.9
redis==5.0.0
celery==5.3.0
PyJWT==2.8.0
cryptography==41.0.0
```

**Note:** Exact versions TBD after checking current compatibility

### [✅] 1.4 Update API Endpoints (backend/main.py)

**File:** `backend/main.py`

**Changes:**

1. Import authentication dependency:
   ```python
   from backend.auth import get_current_user, AuthenticationError
   ```

2. Add authentication exception handler:
   ```python
   @app.exception_handler(AuthenticationError)
   async def auth_exception_handler(request: Request, exc: AuthenticationError):
       return JSONResponse(status_code=401, content={"error": "Unauthorized"})
   ```

3. Protect `/api/submit` endpoint (line 182):
   ```python
   @app.post("/api/submit")
   async def submit_job(
       request: Request,
       course_input: CourseInputRequest,
       background_tasks: BackgroundTasks,
       current_user: dict = Depends(get_current_user)  # ADD THIS
   ):
       user_id = current_user["id"]
       # Pass user_id to create_job()
   ```

4. Protect `/api/status/{job_id}` endpoint (line 267):
   ```python
   @app.get("/api/status/{job_id}")
   async def get_job_status(
       job_id: str,
       current_user: dict = Depends(get_current_user)  # ADD THIS
   ):
       # Verify job belongs to user (RLS will enforce, but double-check)
   ```

5. Protect `/api/cancel/{job_id}` endpoint (line 333):
   ```python
   @app.post("/api/cancel/{job_id}")
   async def cancel_job(
       request: Request,
       job_id: str,
       current_user: dict = Depends(get_current_user)  # ADD THIS
   ):
       # Verify ownership before cancellation
   ```

6. Keep `/api/health` endpoints public (no auth required)

### [✅] 1.5 Update Job Creation (backend/jobs.py)

**File:** `backend/jobs.py`

**Changes in `create_job()` function (line 26):**

1. Add `user_id` parameter:
   ```python
   def create_job(inputs: Dict[str, str], user_id: str) -> str:
   ```

2. Include `user_id` in job data (line 43):
   ```python
   job_data = {
       "user_id": user_id,  # ADD THIS
       "status": "pending",
       "inputs": inputs,
       # ... rest of fields
   }
   ```

3. Update cache lookup to be user-scoped in `backend/cache.py`:
   ```python
   def get_cached_result(inputs: Dict[str, Any], config_hash: str, user_id: str):
       # Add user_id to cache query
   ```

---

## Phase [✅]  2: Input Validation & Prompt Injection Protection

### [✅] 2.1 Create Security Utilities (backend/security_utils.py)

**New file:** `backend/security_utils.py`

**Purpose:** Centralized input validation and prompt injection detection

**Components:**

1. **URL Validation:**
   ```python
   def validate_url(url: str) -> bool:
       """Validate URL format, scheme, and safety"""
       # Check URL is well-formed
       # Reject javascript:, data:, file:// schemes
       # Reject URLs with newlines or control characters
       # Max length check (2048 chars)
   ```

2. **Prompt Injection Detection (STRICT MODE):**
   ```python
   PROMPT_INJECTION_PATTERNS = [
       r'(?:ignore|disregard|bypass|override)\s+(?:your|previous|all)\s+(?:instructions|orders|prompt|rules)',
       r'(?:forget|clear|delete)\s+(?:your|all|previous)',
       r'(?:you are now|act as|pretend to be|roleplay as)\s+\w+',
       r'(?:system\s+)?prompt\s*:',
       r'new\s+(?:instruction|directive|command)',
       r'\$\{.*?\}',  # Template injection
       r'<!--.*?-->',  # HTML comments
       r'<script|<iframe|<object|<embed',  # HTML injection
       r'(?:^|\n)\s*---+\s*(?:\n|$)',  # YAML/Markdown separators
       r'(?:^|\n)\s*```',  # Code blocks
   ]

   def detect_prompt_injection(text: str) -> tuple[bool, str]:
       """Returns (is_suspicious, reason)"""
   ```

3. **Domain Validation:**
   ```python
   def validate_domain_list(domains_csv: str) -> tuple[bool, str]:
       """Validate comma-separated domain list"""
       # Check each domain is valid format
       # Reject IP addresses, localhost, special domains
   ```

4. **General Text Sanitization:**
   ```python
   def validate_text_input(text: str, max_length: int = 500) -> tuple[bool, str]:
       """Validate general text input for prompt safety"""
       # Check length
       # Check for excessive newlines
       # Check for control characters
       # Check for suspicious patterns
   ```

###[✅]  2.2 Update Pydantic Models (backend/models.py)

**File:** `backend/models.py`

**Add validators to `CourseInputRequest` model:**

1. Import security utilities (top of file):
   ```python
   from backend.security_utils import (
       validate_url,
       detect_prompt_injection,
       validate_domain_list,
       validate_text_input
   )
   ```

2. Add URL validators:
   ```python
   @field_validator('course_url', 'book_url', mode='after')
   @classmethod
   def validate_urls(cls, v):
       if v is None or v == "":
           return v

       is_valid = validate_url(v)
       if not is_valid:
           raise ValueError(f"Invalid URL format: {v}")

       # Check for prompt injection in URL
       is_suspicious, reason = detect_prompt_injection(v)
       if is_suspicious:
           raise ValueError(f"Suspicious URL pattern detected: {reason}")

       return v
   ```

3. Add text field validators:
   ```python
   @field_validator('book_title', 'book_author', 'textbook', mode='after')
   @classmethod
   def validate_text_fields(cls, v):
       if v is None or v == "":
           return v

       is_valid, error = validate_text_input(v, max_length=200)
       if not is_valid:
           raise ValueError(error)

       is_suspicious, reason = detect_prompt_injection(v)
       if is_suspicious:
           raise ValueError(f"Input contains suspicious patterns: {reason}")

       return v
   ```

4. Add topics_list validator:
   ```python
   @field_validator('topics_list', mode='after')
   @classmethod
   def validate_topics(cls, v):
       if v is None or v == "":
           return v

       is_valid, error = validate_text_input(v, max_length=500)
       if not is_valid:
           raise ValueError(error)

       # Topics list can contain commas, but check for injection
       is_suspicious, reason = detect_prompt_injection(v)
       if is_suspicious:
           raise ValueError(f"Topics list contains suspicious patterns: {reason}")

       return v
   ```

5. Add domain list validators:
   ```python
   @field_validator('excluded_sites', 'targeted_sites', mode='after')
   @classmethod
   def validate_sites(cls, v):
       if v is None or v == "":
           return v

       is_valid, error = validate_domain_list(v)
       if not is_valid:
           raise ValueError(error)

       return v
   ```

6. Add ISBN validator:
   ```python
   @field_validator('isbn', mode='after')
   @classmethod
   def validate_isbn(cls, v):
       if v is None or v == "":
           return v

       # Remove hyphens and spaces
       clean_isbn = v.replace('-', '').replace(' ', '')

       # Check length (ISBN-10 or ISBN-13)
       if len(clean_isbn) not in [10, 13]:
           raise ValueError("ISBN must be 10 or 13 digits")

       if not clean_isbn.isdigit():
           raise ValueError("ISBN must contain only digits")

       return v
   ```

### [✅] 2.3 Add Secondary Validation Layer (backend/tasks.py)

**File:** `backend/tasks.py`

**Purpose:** Defense-in-depth - validate inputs again before passing to LLM

**Changes in `run_crew_task()` function (after line 110):**

```python
# After normalizing inputs, validate again for safety
from backend.security_utils import detect_prompt_injection

for key, value in normalized_inputs.items():
    if isinstance(value, str) and value:
        is_suspicious, reason = detect_prompt_injection(value)
        if is_suspicious:
            error_msg = f"Input validation failed for '{key}': {reason}"
            logger.error(f"🚨 Prompt injection attempt blocked in job {job_id}: {error_msg}")
            update_job(
                job_id=job_id,
                status="failed",
                error=error_msg,
                status_message="Input validation failed"
            )
            return {"error": error_msg}
```

###[✅] 2.4 Update Error Messages (backend/error_utils.py)

**File:** `backend/error_utils.py`

**Add pattern matching for validation errors in `transform_error_for_user()` (around line 40):**

```python
# Handle validation errors from Pydantic
if isinstance(exception, ValueError) and "suspicious" in str(exception).lower():
    return (
        "Your input contains patterns that may interfere with processing. "
        "Please remove any special formatting, instructions, or unusual characters and try again.",
        "ValidationError"
    )
```

### [ ] 2.5 Prompt Injection Protection Enhancement

**Task:** Revamp existing prompt injection detection implementation in [backend/security_utils.py](backend/security_utils.py) to strengthen protection against prompt injection attacks.

**Current Issue:** The existing `PROMPT_INJECTION_PATTERNS` (line 229) provides basic detection but is insufficient for comprehensive protection against sophisticated prompt injection attacks.

**Required Improvements:**

1. **Enhance Pattern Detection:**
   - Add patterns for indirect prompt injection (e.g., "Repeat after me", "Translate this", "Summarize the following")
   - Detect role confusion attacks ("You are a helpful assistant who...", "As an AI...")
   - Catch instruction leakage attempts ("Show your system prompt", "What are your instructions")
   - Detect delimiter/boundary attacks (unusual Unicode, zero-width characters, mixed scripts)
   - Add patterns for goal hijacking ("Your new task is...", "Priority override...")

2. **Multi-Layer Analysis:**
   - Implement entropy analysis to detect gibberish or encoded payloads
   - Check for excessive special characters or unusual character distributions
   - Detect base64/hex encoded strings that might contain hidden instructions
   - Analyze semantic similarity to known attack vectors using embeddings (optional, performance-dependent)

3. **Context-Aware Validation:**
   - Different validation strictness for different input fields (URLs vs. free text vs. domains)
   - Whitelist approach for structured fields (ISBN, domains) rather than blacklist
   - Length and complexity limits per field type

4. **Logging and Monitoring:**
   - Log all blocked attempts with pattern matches for analysis
   - Track false positive rates to tune patterns
   - Create alert system for repeated injection attempts from same user/IP

5. **Testing:**
   - Create comprehensive test suite with known prompt injection attacks
   - Test against OWASP LLM Top 10 prompt injection examples
   - Include adversarial examples and edge cases
   - Regular updates as new attack vectors emerge

**Priority:** HIGH - Current implementation provides basic protection but needs hardening

**Status:** Pending

---

## Phase [✅] 3: Email HTML Injection Fix

### [✅] 3.1 Update Email Service (backend/email_service.py)

**File:** `backend/email_service.py`

**Changes in `_build_email_html()` function:**

1. Import HTML escaping (top of file):
   ```python
   import html
   ```

2. Escape all user-provided data before embedding in HTML (lines 88-114):
   ```python
   # Escape data to prevent HTML injection
   resource_type = html.escape(resource.get("type", "Resource"))
   title = html.escape(resource.get("title", "Untitled"))
   url_raw = resource.get("url", "#")
   url = html.escape(url_raw)  # Escape for display
   source = html.escape(resource.get("source", "Unknown"))
   description = html.escape(resource.get("description", "")) if resource.get("description") else ""

   # Validate URL before using as href
   if not validate_url(url_raw):
       url_raw = "#"  # Use placeholder if URL is invalid

   resources_html += f"""
   <div style="...">
       <span>...{resource_type}</span>
       <strong>{title}</strong>
       <a href="{url_raw}">  <!-- Use raw URL for href, escaped URL for display -->
           {url}
       </a>
       <div><strong>Source:</strong> {source}</div>
       {f'<div>{description}</div>' if description else ''}
   </div>
   """
   ```

3. Escape search_title (line 136):
   ```python
   search_title_escaped = html.escape(search_title)
   # Use search_title_escaped in HTML
   ```

4. Escape job_id (already safe as UUID, but for consistency):
   ```python
   job_id_escaped = html.escape(job_id)
   ```

### [✅] 3.2 Add Email Validation Tests (tests/unit/test_email_service.py)

**New file:** `tests/unit/test_email_service.py`

**Test cases:**
1. Test HTML injection in resource title
2. Test JavaScript URL in resource URL
3. Test XSS in description field
4. Test script tags in source field
5. Test that legitimate HTML entities are properly escaped
6. Test search_title with HTML characters

---

## Phase [✅] 4: Secrets Management & Dependencies

### [✅] 4.1 Pin All Dependencies (requirements.txt)

**File:** `requirements.txt`

**Update to use exact/pessimistic versions:**

```
# Core dependencies (exact pinning after version audit)
crewai[tools]==0.120.1
lancedb==0.25.0
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
pydantic[email]==2.9.2
supabase==2.9.1
python-dotenv==1.0.1
resend==0.8.0
slowapi==0.1.9
redis==5.2.0
celery==5.4.0
PyJWT==2.9.0
cryptography==42.0.8

# Tools and utilities
beautifulsoup4==4.12.3
requests==2.32.3
```

**Note:** Actual versions to be determined by running `pip freeze` after testing

### [✅] 4.2 Update pyproject.toml

**File:** `pyproject.toml`

Mirror the pinned versions from requirements.txt in the dependencies section.

### [✅] 4.3 Update .gitignore (add missing entries)

**File:** `.gitignore`

**Add:**
```
# Additional secrets and sensitive files
.secrets/
*.secret
*.key
*.pem
secrets.json
credentials.json

# Dependency lock files (if using alternative package managers)
Pipfile.lock
uv.lock
poetry.lock

# Database files
*.db
*.sqlite
*.sqlite3
*.dump
*.sql.backup

# Additional IDE secrets
.vscode/secrets.json
.idea/workspace.xml
```

### [✅] 4.4 Verify .env.local is not in Git

**Action:** Run git command to remove .env.local if present in history

```bash
git rm --cached .env.local
git commit -m "Remove .env.local from version control"
```

### [✅] 4.5 Enhance Error Sanitization (backend/error_utils.py)

**File:** `backend/error_utils.py`

**Enhancement to `sanitize_error_message()` (add to line 162):**

```python
# Additional: mask Supabase keys, JWT tokens
message = re.sub(r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', '[JWT_TOKEN]', message)
message = re.sub(r'sb-[a-zA-Z0-9-]+', '[SUPABASE_KEY]', message)
```

---

## Phase [✅] 5: Frontend Authentication Integration

### [✅] 5.1 Add Supabase Client (web/)

**Install dependency:**
```bash
cd web && npm install @supabase/supabase-js
```

**New file:** `web/src/lib/supabase.js`

**Purpose:** Initialize Supabase client for frontend

```javascript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
});
```

### [✅] 5.2 Create Auth Context (web/src/contexts/AuthContext.jsx)

**New file:** `web/src/contexts/AuthContext.jsx`

**Purpose:** Manage authentication state across the app

```javascript
import { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext({});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check active sessions
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return data;
  };

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  return (
    <AuthContext.Provider value={{ user, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### [✅] 5.3 Create Auth UI Components

**New file:** `web/src/components/Auth/LoginForm.jsx`

**Purpose:** Email/password login form

**Features:**
- Email and password inputs
- Form validation
- Error display
- Link to signup

**New file:** `web/src/components/Auth/SignupForm.jsx`

**Purpose:** Email/password signup form

**Features:**
- Email, password, confirm password inputs
- Password strength validation
- Error display
- Link to login

**New file:** `web/src/components/Auth/AuthPage.jsx`

**Purpose:** Combined auth page with tab switching

**Features:**
- Tabs for Login/Signup
- Conditional rendering based on state
- Redirect to app after successful auth

### [✅] 5.4 Update API Client (web/src/api/client.js)

**File:** `web/src/api/client.js`

**Changes:**

1. Import Supabase client (top of file):
   ```javascript
   import { supabase } from '../lib/supabase';
   ```

2. Add helper to get JWT token:
   ```javascript
   async function getAuthToken() {
     const { data: { session } } = await supabase.auth.getSession();
     return session?.access_token;
   }
   ```

3. Update `submitCourseInput()` to include auth header (line 37):
   ```javascript
   export async function submitCourseInput(inputs) {
     const cleanedInputs = cleanInputs(inputs);
     const token = await getAuthToken();

     if (!token) {
       throw new Error('You must be logged in to submit a job');
     }

     const response = await fetch(`${API_BASE_URL}/api/submit`, {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
         'Authorization': `Bearer ${token}`  // ADD THIS
       },
       body: JSON.stringify(cleanedInputs),
     });

     // Handle 401 Unauthorized
     if (response.status === 401) {
       throw new Error('Authentication failed. Please log in again.');
     }

     // ... rest of function
   }
   ```

4. Update `getJobStatus()` similarly:
   ```javascript
   export async function getJobStatus(jobId) {
     const token = await getAuthToken();

     const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`, {
       headers: {
         'Authorization': `Bearer ${token}`
       }
     });

     if (response.status === 401) {
       throw new Error('Authentication failed');
     }

     // ... rest
   }
   ```

5. Update `cancelJob()` similarly

### [✅] 5.5 Update App Entry Point (web/src/App.jsx)

**File:** `web/src/App.jsx`

**Changes:**

1. Import AuthProvider and AuthPage:
   ```javascript
   import { AuthProvider, useAuth } from './contexts/AuthContext';
   import AuthPage from './components/Auth/AuthPage';
   ```

2. Wrap app with AuthProvider:
   ```javascript
   function App() {
     return (
       <AuthProvider>
         <AppContent />
       </AuthProvider>
     );
   }
   ```

3. Create protected app content component:
   ```javascript
   function AppContent() {
     const { user, loading } = useAuth();

     if (loading) {
       return <div>Loading...</div>;  // Or a proper loading spinner
     }

     if (!user) {
       return <AuthPage />;  // Show login/signup if not authenticated
     }

     return (
       <div className="app">
         {/* Existing app content */}
         <InputForm />
         <ResultsPanel />
       </div>
     );
   }
   ```

### [✅] 5.6 Add User Menu Component (web/src/components/UserMenu.jsx)

**New file:** `web/src/components/UserMenu.jsx`

**Purpose:** Display user email and logout button

**Features:**
- Show current user's email
- Logout button
- Positioned in app header/nav

### [✅] 5.7 Add Environment Variables (web/.env.local)

**File:** `web/.env.local` (create if not exists)

**Content:**
```
VITE_SUPABASE_URL=https://[your-project].supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...  # From Supabase dashboard
VITE_API_BASE_URL=http://localhost:8000  # Or production URL
```

**Ensure:** This file is in .gitignore (already is)

### [✅] 5.8 Update CORS Configuration (backend/main.py)

**File:** `backend/main.py`

**No changes needed** - CORS already configured correctly for localhost and production domains

---

## Phase [✅] 6: Testing & Validation

### [✅] 6.1 Create Security Tests (tests/unit/test_security_utils.py)

**New file:** `tests/unit/test_security_utils.py`

**Test cases:**
1. ✅ URL validation - valid URLs pass
2. ✅ URL validation - invalid URLs fail (javascript:, data:, file://)
3. ✅ URL validation - URLs with newlines fail
4. ✅ Prompt injection detection - common patterns caught
5. ✅ Prompt injection detection - legitimate text passes
6. ✅ Domain list validation - valid domains pass
7. ✅ Domain list validation - invalid domains fail
8. ✅ Text input validation - normal text passes
9. ✅ Text input validation - excessive length fails
10. ✅ Text input validation - control characters fail

**Status:** All 53 security utility tests passing

### [✅] 6.2 Update Model Tests (tests/unit/test_models.py)

**File:** `tests/unit/test_models.py`

**Add test cases:**
1. ✅ Test URL validation in course_url field
2. ✅ Test URL validation in book_url field
3. ✅ Test prompt injection detection in book_title
4. ✅ Test prompt injection detection in topics_list
5. ✅ Test ISBN validation - valid ISBNs
6. ✅ Test ISBN validation - invalid ISBNs
7. ✅ Test domain validation in excluded_sites
8. ✅ Test domain validation in targeted_sites

**Status:** All 22 model security validation tests passing

### [✅] 6.3 Create Authentication Tests (tests/integration/test_auth.py)

**New file:** `tests/integration/test_auth.py`

**Test cases:**
1. ✅ POST /api/submit without token returns 401
2. ✅ POST /api/submit with invalid token returns 401
3. ✅ POST /api/submit with valid token succeeds
4. ✅ GET /api/status without auth returns 401
5. ✅ Users can only access their own jobs
6. ✅ Users cannot access other users' jobs
7. ✅ Job creation associates job with authenticated user

**Status:** 17+ authentication integration tests passing

### [✅] 6.4 Create Email Security Tests (tests/unit/test_email_service.py)

**Test cases covered in Phase 3.2**

**Status:** All 11 email HTML escaping tests passing

---

## Phase 7: Documentation & Migration

### 7.1 Update README.md

**File:** `README.md`

**Add sections:**
1. **Authentication Setup:**
   - How to get Supabase credentials
   - Environment variable configuration
   - First-time setup instructions

2. **Security Features:**
   - Authentication requirement
   - Input validation
   - Prompt injection protection
   - Rate limiting

3. **Development:**
   - How to run with authentication locally
   - How to create test users
   - How to bypass auth for testing (if needed)


## Critical Files to Modify

### Backend:
1. `supabase_schema.sql` - Database schema changes
2. `backend/auth.py` - NEW - Authentication middleware
3. `backend/security_utils.py` - NEW - Input validation
4. `backend/models.py` - Add validators
5. `backend/main.py` - Add auth dependencies to endpoints
6. `backend/jobs.py` - Add user_id parameter
7. `backend/cache.py` - Add user_id to cache queries
8. `backend/tasks.py` - Add secondary validation
9. `backend/email_service.py` - Add HTML escaping
10. `backend/error_utils.py` - Add validation error handling
11. `requirements.txt` - Pin versions, add PyJWT
12. `pyproject.toml` - Mirror requirements changes
13. `.gitignore` - Add missing entries

### Frontend:
14. `web/package.json` - Add @supabase/supabase-js
15. `web/src/lib/supabase.js` - NEW - Supabase client
16. `web/src/contexts/AuthContext.jsx` - NEW - Auth state
17. `web/src/components/Auth/LoginForm.jsx` - NEW
18. `web/src/components/Auth/SignupForm.jsx` - NEW
19. `web/src/components/Auth/AuthPage.jsx` - NEW
20. `web/src/components/UserMenu.jsx` - NEW
21. `web/src/api/client.js` - Add JWT headers
22. `web/src/App.jsx` - Wrap with AuthProvider, protect routes
23. `web/.env.local` - Add Supabase credentials

### Testing:
24. `tests/unit/test_security_utils.py` - NEW
25. `tests/unit/test_models.py` - Update with validation tests
26. `tests/unit/test_email_service.py` - NEW
27. `tests/integration/test_auth.py` - NEW

### Documentation:
28. `README.md` - Update with auth setup
29. `MIGRATION.md` - NEW - Migration guide
30. `backend/.env.example` - Add JWT secret
31. `web/.env.example` - NEW - Frontend env vars

---

## Implementation Order

### Priority 1 - Critical Security (Do First):
1. Email HTML escaping (Phase 3) - **CRITICAL** vulnerability
2. Input validation & prompt injection (Phase 2) - **HIGH** risk
3. Dependency pinning (Phase 4.1-4.2) - **HIGH** risk

### Priority 2 - Authentication (Required for Production):
4. Database schema changes (Phase 1.1)
5. Backend authentication middleware (Phase 1.2-1.5)
6. Frontend authentication (Phase 5)

### Priority 3 - Finalization:
7. Secrets management (Phase 4.3-4.5)
8. Testing (Phase 6)
9. Documentation (Phase 7)

---

## Verification Steps

### After Phase 1-2 (Backend Security):
1. Run backend tests: `pytest tests/unit/test_security_utils.py`
2. Run model tests: `pytest tests/unit/test_models.py`
3. Test API endpoint with missing auth token (should return 401)
4. Test API endpoint with invalid auth token (should return 401)
5. Verify database RLS policies work in Supabase dashboard

### After Phase 3 (Email Security):
1. Run email tests: `pytest tests/unit/test_email_service.py`
2. Send test email with malicious HTML in title/description
3. Verify HTML is escaped in received email

### After Phase 4 (Dependencies):
1. Create fresh virtual environment
2. Install from requirements.txt
3. Verify all dependencies install with pinned versions
4. Run full test suite
5. Verify .env.local not in git: `git ls-files | grep .env.local` (should be empty)

### After Phase 5 (Frontend):
1. Start frontend dev server: `cd web && npm run dev`
2. Verify login form appears when not authenticated
3. Create test user account
4. Verify successful login redirects to main app
5. Verify JWT token included in API requests (check Network tab)
6. Test logout functionality
7. Verify session persists on page reload

### End-to-End Test:
1. Sign up as new user
2. Submit a job with various inputs
3. Verify job appears in status check
4. Try to access job with different user (should fail)
5. Test prompt injection patterns in inputs (should be rejected)
6. Test malicious URLs (should be rejected)
7. Complete job and receive email
8. Verify email HTML is properly escaped
9. Test logout and login again
10. Verify old jobs still accessible after re-login

---

## Risk Mitigation

### Rollback Plan:
- Keep backup of current database schema
- Git tag before starting changes
- Test in staging environment first
- Have database restore procedure ready

### Backward Compatibility:
- Authentication breaks existing anonymous usage (intentional per requirements)
- All existing jobs will be deleted (per "start fresh" preference)
- Frontend will require login immediately
- API clients will need to be updated with auth tokens

### Performance Considerations:
- JWT verification adds ~5ms per request (negligible)
- Input validation adds ~2-10ms per request (acceptable)
- User-specific cache reduces efficiency but improves privacy (acceptable tradeoff)
- RLS policies add minimal database overhead (~1-2ms)

---

## Notes

- Supabase JWT secret can be found in Supabase Dashboard > Settings > API > JWT Secret
- Supabase automatically handles token refresh, we just need to verify tokens on backend
- RLS policies provide defense-in-depth even if backend validation fails
- Strict prompt injection mode may have false positives - monitor logs and adjust patterns if needed
- Email HTML escaping is backward compatible - no migration needed for existing emails
- All dependency versions should be tested in staging before deploying to production

---

## Success Criteria

✅ No authentication = 401 Unauthorized
✅ Users can only access their own jobs
✅ Prompt injection patterns are blocked
✅ Malicious URLs are rejected
✅ Email HTML is properly escaped
✅ All dependencies have pinned versions
✅ Secrets not in git history
✅ All tests pass
✅ Frontend auth flow works end-to-end
✅ Existing functionality preserved (with auth requirement)
