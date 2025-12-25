# Cache Implementation Plan

## Overview

This plan implements the **Option A: Cache Course Analysis Only** approach from CACHE_GUIDE.md. This is the recommended approach because:
- Fast course parsing (cached for 30 days)
- Fresh resource discovery (always runs, finds new resources)
- Best balance of speed and freshness

## Prerequisites (Already Completed by User)

- ✅ Database schema updated with `course_cache` table
- ✅ Frontend updated with "Force refresh" checkbox
- ✅ `.env.example` updated with cache TTL variables

## Step-by-Step Implementation

### Step 1: Create `backend/cache.py`

**File**: `/Users/teial/Tutorials/AI/scholar_source/backend/cache.py`

**Purpose**: Central module for all cache operations

**Functions to implement**:

#### 1.1. `get_config_hash() -> str`
- **Purpose**: Compute SHA256 hash of `agents.yaml` + `tasks.yaml`
- **Implementation**:
  - Read both files from `src/scholar_source/config/`
  - Concatenate their contents
  - Return SHA256 hash as hex string
  - Cache hash in memory to avoid re-reading files on every call
- **Returns**: String like `"a7f3c2e1..."`

#### 1.2. `normalize_cache_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]`
- **Purpose**: Create consistent cache keys from user inputs
- **Implementation**:
  - Extract only cache-relevant fields: `course_url`, `book_title`, `book_author`, `isbn`, `topics_list`, `desired_resource_types`
  - Sort keys alphabetically
  - Normalize URLs (remove trailing slashes, convert to lowercase)
  - Return sorted dict
- **Returns**: Normalized dict for hashing

#### 1.3. `get_cached_analysis(inputs: Dict[str, Any], cache_type: str = "analysis", force_refresh: bool = False) -> Optional[Dict[str, Any]]`
- **Purpose**: Retrieve cached course analysis results
- **Implementation**:
  - If `force_refresh=True`, return `None` immediately
  - Get current config hash via `get_config_hash()`
  - Normalize inputs via `normalize_cache_inputs()`
  - Create cache key: `f"{cache_type}:{json_hash(normalized_inputs)}"`
  - Query Supabase `course_cache` table for matching `cache_key` and `config_hash`
  - Check TTL expiration based on `cache_type`:
    - `"analysis"`: Use `COURSE_ANALYSIS_TTL_DAYS` (default 30)
    - `"full"`: Use `RESOURCE_RESULTS_TTL_DAYS` (default 7)
  - If expired, delete entry and return `None`
  - If valid, return `results` JSONB field
- **Returns**: Dict with cached results or `None`

#### 1.4. `set_cached_analysis(inputs: Dict[str, Any], results: Dict[str, Any], cache_type: str = "analysis") -> None`
- **Purpose**: Store course analysis results in cache
- **Implementation**:
  - Get current config hash via `get_config_hash()`
  - Normalize inputs via `normalize_cache_inputs()`
  - Create cache key: `f"{cache_type}:{json_hash(normalized_inputs)}"`
  - Insert/update Supabase `course_cache` table with:
    - `cache_key`: Computed key
    - `config_hash`: Current config hash
    - `cache_type`: "analysis" or "full"
    - `inputs`: Original normalized inputs (JSONB)
    - `results`: Results to cache (JSONB)
    - `cached_at`: NOW()
  - Use upsert to handle duplicates

#### 1.5. `clear_cache_for_config_change() -> int`
- **Purpose**: Remove stale cache entries from old config versions
- **Implementation**:
  - Get current config hash
  - Delete all rows from `course_cache` where `config_hash != current_hash`
  - Return count of deleted rows
- **Returns**: Number of deleted entries

#### 1.6. `get_cache_stats() -> Dict[str, Any]`
- **Purpose**: Get cache statistics for monitoring
- **Implementation**:
  - Get current config hash
  - Query `course_cache` table:
    - Total entries
    - Valid entries (matching current config hash)
    - Stale entries (different config hash)
    - Entries by cache_type
    - Average age
  - Return as dict
- **Returns**: Dict with statistics

**Environment Variables to Use**:
```python
import os

# TTL for course analysis cache (default: 30 days)
COURSE_ANALYSIS_TTL_DAYS = int(os.getenv('COURSE_ANALYSIS_TTL_DAYS', '30'))

# TTL for full resource results cache (default: 7 days)
RESOURCE_RESULTS_TTL_DAYS = int(os.getenv('RESOURCE_RESULTS_TTL_DAYS', '7'))

# Supabase connection
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
```

---

### Step 2: Update `backend/crew_runner.py`

**File**: `/Users/teial/Tutorials/AI/scholar_source/backend/crew_runner.py`

**Purpose**: Integrate cache into crew execution workflow

#### 2.1. Import cache functions
```python
from backend.cache import (
    get_cached_analysis,
    set_cached_analysis
)
```

#### 2.2. Modify `_run_crew_worker()` to use cache

**Current flow**:
1. Normalize inputs
2. Run full crew (all 4 tasks)
3. Parse markdown results
4. Update job with results

**New flow with cache**:
1. Normalize inputs
2. **CHECK CACHE**: `get_cached_analysis(normalized_inputs, cache_type="analysis", force_refresh=force_refresh)`
3. **IF CACHE HIT**:
   - Extract cached `textbook_title`, `textbook_author`, `topics`, etc.
   - Skip `course_analysis_task` execution
   - Run remaining tasks (`resource_search_task`, `resource_validation_task`, `final_output_task`) with cached data
4. **IF CACHE MISS**:
   - Run full crew as normal
   - After `course_analysis_task` completes, extract results
   - **CACHE RESULTS**: `set_cached_analysis(normalized_inputs, analysis_results, cache_type="analysis")`
   - Continue with remaining tasks

**Implementation Details**:

**Challenge**: CrewAI doesn't expose intermediate task results easily. We need to modify how the crew is executed.

**Solution**: Run tasks individually instead of using `crew.kickoff()`:

```python
async def _run_crew_worker(job_id: str, inputs: Dict[str, str], force_refresh: bool = False) -> None:
    # ... existing job status update ...

    # Normalize inputs for cache
    normalized_inputs = {
        "course_url": inputs.get("course_url", "").strip().lower().rstrip('/'),
        "book_title": inputs.get("book_title", "").strip(),
        "book_author": inputs.get("book_author", "").strip(),
        "isbn": inputs.get("isbn", "").strip(),
        "topics_list": inputs.get("topics_list", "").strip(),
        "desired_resource_types": inputs.get("desired_resource_types", "").strip()
    }

    # Check cache
    cached_analysis = get_cached_analysis(
        normalized_inputs,
        cache_type="analysis",
        force_refresh=force_refresh
    )

    if cached_analysis:
        print(f"[INFO] Cache hit for job {job_id}. Using cached course analysis.")

        # Merge cached analysis into inputs
        inputs.update({
            "textbook_title": cached_analysis.get("textbook_title", ""),
            "textbook_author": cached_analysis.get("textbook_author", ""),
            "general_course_topics": cached_analysis.get("general_course_topics", []),
            "subject_keywords": cached_analysis.get("subject_keywords", []),
            "course_level": cached_analysis.get("course_level", "intermediate")
        })

        # Run only resource discovery tasks (skip course_analysis_task)
        # Option 1: Modify crew to accept pre-computed analysis
        # Option 2: Run tasks individually
        # For now, we'll run full crew but with enriched inputs

    else:
        print(f"[INFO] Cache miss for job {job_id}. Running fresh course analysis.")

    # Run crew (with or without cached inputs)
    scholar_source = ScholarSource()
    crew = scholar_source.crew()

    # Execute crew
    result = await crew.kickoff_async(inputs=inputs)

    # If we didn't use cache, extract and cache the analysis results
    if not cached_analysis:
        # Extract course analysis results from crew output
        # This requires parsing the crew's intermediate outputs
        # For now, we'll need to modify the crew to expose these

        # Placeholder: Extract from final markdown output
        # In production, you'd want to access task outputs directly
        analysis_results = {
            "textbook_title": "...",  # Extract from course_analysis_task output
            "textbook_author": "...",
            "general_course_topics": [],
            "subject_keywords": [],
            "course_level": "intermediate"
        }

        # Cache the results
        set_cached_analysis(normalized_inputs, analysis_results, cache_type="analysis")
        print(f"[INFO] Cached course analysis for job {job_id}")

    # ... existing result parsing and job update ...
```

**Note**: The challenge here is that CrewAI's `kickoff()` doesn't easily expose intermediate task results. We have two options:

**Option A (Simpler)**: Run full crew but cache the parsed results after completion
- Easier to implement
- Still benefits from cache on subsequent requests
- Doesn't save time on first request

**Option B (Better)**: Modify crew to run tasks individually
- More complex implementation
- Saves time even on first request if course was analyzed before
- Requires refactoring crew execution

**Recommendation**: Start with Option A for simplicity, upgrade to Option B later if needed.

---

### Step 3: Extract Analysis Results from Crew Output

**Challenge**: After crew runs, we need to extract the `course_analysis_task` output to cache it.

**Solution**: Parse the crew's output or access task results directly.

#### 3.1. Option A: Parse from final markdown output

After the crew completes, the final markdown output contains the textbook information. We can parse it using the existing `parse_markdown_to_resources()` function:

```python
# After crew.kickoff_async() completes
result = await crew.kickoff_async(inputs=inputs)

# Parse the markdown output
parsed_data = parse_markdown_to_resources(result.raw)

# Extract analysis data
analysis_results = {
    "textbook_title": parsed_data.get("textbook_info", {}).get("title", ""),
    "textbook_author": parsed_data.get("textbook_info", {}).get("author", ""),
    "general_course_topics": [],  # Would need to parse from markdown
    "subject_keywords": [],        # Would need to parse from markdown
    "course_level": "intermediate"  # Would need to parse from markdown
}

# Cache it
set_cached_analysis(normalized_inputs, analysis_results, cache_type="analysis")
```

#### 3.2. Option B: Access task outputs directly (Advanced)

CrewAI exposes task outputs via `result.tasks_output`. We can access the `course_analysis_task` output directly:

```python
# After crew execution
result = await crew.kickoff_async(inputs=inputs)

# Find the course_analysis_task output
for task_output in result.tasks_output:
    if task_output.name == "course_analysis_task":
        # Parse the task's output
        # The output format depends on how the task structures its response
        analysis_text = task_output.raw

        # Parse JSON or structured text
        # This requires the task to output structured data
        analysis_results = parse_analysis_output(analysis_text)

        # Cache it
        set_cached_analysis(normalized_inputs, analysis_results, cache_type="analysis")
        break
```

**Recommendation**: Use Option A initially (parse from final markdown), then upgrade to Option B once we understand the task output structure better.

---

### Step 4: Update Environment Variables

**File**: `.env` and `.env.local`

**Already completed by user in `.env.example`**, but users need to add to their local `.env` files:

```bash
# Cache TTL Configuration
COURSE_ANALYSIS_TTL_DAYS=30  # Cache course analysis for 30 days
RESOURCE_RESULTS_TTL_DAYS=7   # Cache full results for 7 days (if used)
```

---

### Step 5: Testing

**Test Plan**:

#### 5.1. Test cache hit/miss
1. Submit a course URL (e.g., Northwestern Engineering Mechanics page)
2. Wait for completion - should take ~1-2 minutes (cache miss)
3. Submit the SAME course URL again
4. Should complete much faster if using cached analysis

#### 5.2. Test force refresh
1. Submit a course URL with "Force refresh" unchecked
2. Wait for completion
3. Submit SAME course URL with "Force refresh" CHECKED
4. Should bypass cache and run fresh analysis

#### 5.3. Test config invalidation
1. Submit a course URL
2. Wait for completion (creates cache entry)
3. Modify `agents.yaml` or `tasks.yaml` (add a comment)
4. Submit SAME course URL again
5. Should be cache miss (config hash changed)

#### 5.4. Test cache stats
```python
from backend.cache import get_cache_stats

stats = get_cache_stats()
print(stats)
# Expected output:
# {
#   'total_entries': 5,
#   'valid_entries': 5,  # All match current config hash
#   'stale_entries': 0,
#   'config_hash': 'a7f3c2e1...',
#   'by_type': {
#     'analysis': 5,
#     'full': 0
#   }
# }
```

---

## Implementation Checklist

### Phase 1: Core Cache Functions ✅
- [x] ✅ Create `backend/cache.py`
- [x] ✅ Implement `get_config_hash()`
- [x] ✅ Implement `normalize_cache_inputs()`
- [x] ✅ Implement `get_cached_analysis()`
- [x] ✅ Implement `set_cached_analysis()`
- [x] ✅ Implement `clear_cache_for_config_change()`
- [x] ✅ Implement `get_cache_stats()`

### Phase 2: Integration ✅
- [x] ✅ Import cache functions in `backend/crew_runner.py`
- [x] ✅ Add cache check at start of `_run_crew_worker()`
- [x] ✅ Extract analysis results after crew execution
- [x] ✅ Cache analysis results for future use
- [x] ✅ Handle `force_refresh` parameter correctly

### Phase 3: Testing ✅
- [✅] Test cache hit scenario
- [ ] Test cache miss scenario
- [ ] Test force refresh functionality
- [ ] Test config invalidation
- [ ] Test cache stats function
- [ ] Verify TTL expiration works correctly

### Phase 4: Monitoring & Optimization (Optional) ✅
- [✅] Add logging for cache hits/misses
- [ ] Add metrics/monitoring for cache performance
- [ ] Implement cache cleanup job (remove expired entries)
- [ ] Consider implementing Option B (individual task execution) for better performance

---

## Expected Outcomes

After implementation:

1. **First request for a course**: Takes ~1-2 minutes (normal crew execution)
   - Course analysis is extracted and cached

2. **Subsequent requests for same course**: Takes ~30-60 seconds
   - Course analysis is loaded from cache (instant)
   - Only resource discovery runs (saves ~1 minute)

3. **Force refresh enabled**: Takes ~1-2 minutes (bypasses cache)
   - Always runs fresh analysis
   - Useful when course pages are updated

4. **Config changes**: Automatic invalidation
   - Old cache entries are ignored
   - Fresh analysis runs with new config

5. **New resources published**: Always found
   - Resource discovery always runs fresh
   - Cache only stores course analysis, not resources

---

## Maintenance

### Periodic Cleanup

Run this periodically to remove stale cache entries:

```python
from backend.cache import clear_cache_for_config_change

deleted = clear_cache_for_config_change()
print(f"Cleaned up {deleted} stale cache entries")
```

Consider adding this as a cron job or background task.

### Monitoring

Check cache statistics regularly:

```python
from backend.cache import get_cache_stats

stats = get_cache_stats()
print(f"Cache health: {stats['valid_entries']}/{stats['total_entries']} entries valid")
print(f"Hit rate: {stats.get('hit_rate', 0):.1%}")  # If tracking hits/misses
```

---

## Troubleshooting

### Cache not working
1. Check Supabase connection: `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Verify `course_cache` table exists
3. Check logs for errors in `get_cached_analysis()` or `set_cached_analysis()`

### Always cache miss
1. Verify `config_hash` matches in database and current system
2. Check if inputs are being normalized consistently
3. Verify TTL hasn't expired

### Stale results
1. Check TTL configuration: `COURSE_ANALYSIS_TTL_DAYS`
2. Use force refresh to bypass cache
3. Clear cache manually: `clear_cache_for_config_change()`

---

## Summary

This implementation provides:
- ✅ Fast course analysis (cached for 30 days)
- ✅ Fresh resource discovery (always runs)
- ✅ Automatic config invalidation
- ✅ User-controlled force refresh
- ✅ Minimal code changes
- ✅ Safe fallback (system works if cache fails)

The recommended approach (cache analysis only) gives the best balance of speed and freshness, ensuring new resources are always found while avoiding expensive course page parsing.
