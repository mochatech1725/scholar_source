# Course Analysis Cache Guide

## Overview

The cache system stores course analysis results (textbook info, topics) to avoid re-running expensive CrewAI operations for the same course URLs. **Cache keys automatically include a hash of `agents.yaml` and `tasks.yaml`**, ensuring cache invalidation when agent or task configurations change.

## How It Works

1. **Config Hash**: On each cache lookup, the system computes a SHA256 hash of both `agents.yaml` and `tasks.yaml`
2. **Cache Key**: Includes input parameters (course_url, book info, topics, etc.) + config hash
3. **Automatic Invalidation**: If config files change, the hash changes, and old cache entries are automatically invalidated
4. **Time-Based Expiration (TTL)**: Different TTLs for different cache types:
   - **Course Analysis** (textbook extraction, topics): **30 days** - Changes infrequently
   - **Full Resource Results**: **7 days** - New resources may be published over time

## Handling New Data: Two-Tier Caching Strategy

### The Problem

**Question**: "How does cache invalidation account for new data that may be available?"

**Answer**: The cache uses a **two-tier strategy** with different TTLs for different data types.

### Tier 1: Course Analysis (30 days TTL)
- **What**: Textbook extraction, topic identification, course metadata
- **Why Cache**: This is expensive (requires parsing course pages) and changes infrequently
- **TTL**: 30 days (configurable via `COURSE_ANALYSIS_TTL_DAYS`)
- **When Invalidated**:
  - Config files change (agents.yaml, tasks.yaml)
  - TTL expires (30 days)
  - Force refresh requested

### Tier 2: Full Resource Results (7 days TTL)
- **What**: Complete resource discovery results (all found resources)
- **Why Shorter TTL**: New resources may be published online daily
- **TTL**: 7 days (configurable via `RESOURCE_RESULTS_TTL_DAYS`)
- **When Invalidated**:
  - Config files change
  - TTL expires (7 days - ensures fresh results)
  - Force refresh requested

### Recommended Approach: Cache Analysis Only

**Best Practice**: Cache only course analysis, always run resource discovery fresh.

```python
# Cache course analysis (30 days)
cached_analysis = get_cached_analysis(inputs, cache_type="analysis")
if cached_analysis:
    # Use cached textbook info and topics
    textbook_info = cached_analysis.get("textbook_info")
    topics = cached_analysis.get("topics")
else:
    # Run course analysis task
    # ... then cache results ...
    set_cached_analysis(inputs, analysis_results, cache_type="analysis")

# Always run resource discovery fresh (no cache)
# This ensures new resources are found
resources = run_resource_discovery(textbook_info, topics)
```

**Benefits**:
- ✅ Fast course parsing (cached for 30 days)
- ✅ Fresh resource discovery (always current)
- ✅ Best balance of speed and freshness

### Example: Handling New Resources

**Scenario**: A course page was analyzed 5 days ago, but new practice problems were just published.

**With Tier 1 Only (Recommended)**:
```python
# Day 0: First request
analysis = run_course_analysis(course_url)  # Expensive, takes 30s
cache.set(analysis, ttl=30_days)
resources = run_resource_discovery(analysis)  # Finds 5 resources

# Day 5: Second request (new resources published)
analysis = cache.get()  # ✅ Cache hit! (30 days TTL)
resources = run_resource_discovery(analysis)  # ✅ Fresh! Finds 6 resources (new one added)
```

**With Full Caching (7 day TTL)**:
```python
# Day 0: First request
results = run_full_crew(course_url)  # Takes 2 minutes
cache.set(results, ttl=7_days)

# Day 5: Second request (new resources published)
results = cache.get()  # ✅ Cache hit! Returns old 5 resources (misses new one)
# ❌ User doesn't see new resource until Day 8
```

## Database Setup

Run the updated `supabase_schema.sql` to create the `course_cache` table:

```sql
-- Course Analysis Cache Table
-- Stores cached course analysis results to avoid re-running expensive operations
-- Supports two cache types:
--   - 'analysis': Course analysis only (textbook extraction, topics) - TTL: 30 days
--   - 'full': Complete results including resources - TTL: 7 days
CREATE TABLE course_cache (
    cache_key TEXT PRIMARY KEY,  -- Format: "analysis:hash" or "full:hash"
    config_hash TEXT NOT NULL,   -- Hash of agents.yaml + tasks.yaml for auto-invalidation
    cache_type TEXT NOT NULL DEFAULT 'analysis',  -- 'analysis' or 'full'
    inputs JSONB NOT NULL,        -- Original inputs for debugging/auditing
    results JSONB NOT NULL,       -- Cached results
    cached_at TIMESTAMPTZ DEFAULT NOW()  -- Used for TTL expiration
);

-- Indexes for faster lookups
CREATE INDEX idx_course_cache_config_hash ON course_cache(config_hash);
CREATE INDEX idx_course_cache_cached_at ON course_cache(cached_at DESC);
```

## Integration Options

### Option A: Cache Course Analysis Only (Recommended - Best for Fresh Data)

**Why this is recommended**: Course analysis (textbook extraction, topics) changes infrequently, but resource discovery results can change daily as new materials are published. By caching only the analysis, you get:
- Fast course parsing (cached for 30 days)
- Fresh resource discovery (always runs, finds new resources)

Cache the results from `course_analysis_task` (textbook info, topics) and use them to skip the first task if cached:

```python
# In backend/crew_runner.py, modify _run_crew_worker:

from backend.cache import get_cached_analysis, set_cached_analysis

async def _run_crew_worker(job_id: str, inputs: Dict[str, str], force_refresh: bool = False) -> None:
    # ... existing code ...
    
    # Check cache before running crew (cache_type="analysis" for course analysis only)
    cached_results = get_cached_analysis(
        normalized_inputs, 
        cache_type="analysis",
        force_refresh=force_refresh
    )
    
    if cached_results:
        # Use cached course analysis
        textbook_info = cached_results.get("textbook_info")
        topics = cached_results.get("topics")
        
        # Skip course_analysis_task and proceed directly to resource_search_task
        # You'll need to modify the crew to accept pre-computed analysis
        print(f"[INFO] Using cached analysis for job {job_id}")
    else:
        # Run full crew as normal
        # ... existing crew execution ...
        
        # After course_analysis_task completes, extract and cache results
        # (This requires modifying the crew to expose intermediate results)
        analysis_results = {
            "textbook_info": extracted_textbook_info,
            "topics": extracted_topics
        }
        set_cached_analysis(normalized_inputs, analysis_results, cache_type="analysis")
```

**Note**: This requires modifying the crew to expose intermediate task results or running tasks individually.

### Option C: Hybrid Approach (Best Performance)

Cache course analysis separately, and use it to populate task inputs:

```python
# Cache course analysis results, then use them in subsequent tasks
# This avoids re-analyzing the same course page multiple times

cached_analysis = get_cached_analysis(normalized_inputs, cache_type="analysis", force_refresh=force_refresh)
if cached_analysis:
    # Merge cached analysis into inputs for downstream tasks
    normalized_inputs.update({
        "textbook_title": cached_analysis.get("textbook_title"),
        "textbook_author": cached_analysis.get("textbook_author"),
        "cached_topics": cached_analysis.get("topics", [])
    })
```

## Configuration

### Environment Variables

Configure TTLs via environment variables (recommended):

```bash
# Course analysis cache (textbook extraction, topics) - default: 30 days
COURSE_ANALYSIS_TTL_DAYS=30

# Full resource results cache - default: 7 days  
RESOURCE_RESULTS_TTL_DAYS=7
```

### Code Configuration

Or edit `backend/cache.py` directly:

```python
# Course analysis (textbook extraction, topics) changes less frequently
COURSE_ANALYSIS_TTL_DAYS = 30  # Default: 30 days

# Full resource discovery results change more frequently (new resources published)
RESOURCE_RESULTS_TTL_DAYS = 7  # Default: 7 days

# Set to None to disable expiration (not recommended)
# COURSE_ANALYSIS_TTL_DAYS = None
```

### TTL Recommendations

**For More Freshness** (find new resources more often):
```bash
RESOURCE_RESULTS_TTL_DAYS=3  # Check for new resources every 3 days
COURSE_ANALYSIS_TTL_DAYS=14  # Re-parse course pages every 2 weeks
```

**For More Performance** (fewer API calls):
```bash
RESOURCE_RESULTS_TTL_DAYS=14  # Cache results for 2 weeks
COURSE_ANALYSIS_TTL_DAYS=60   # Cache analysis for 2 months
```

**For Development/Testing**:
```bash
RESOURCE_RESULTS_TTL_DAYS=1   # Cache for 1 day only
COURSE_ANALYSIS_TTL_DAYS=1    # Cache for 1 day only
```

**General Guidelines**:
- **Course Analysis**: 30-90 days (textbook info rarely changes)
- **Full Results**: 3-7 days (new resources may be published)
- **Development/Testing**: 1 day or less

## Force Refresh

Users can force a refresh to bypass the cache and get fresh results. This is useful when:
- New resources may have been published
- Course pages have been updated
- You want to test with the latest agent configurations
- You suspect cached results are stale

### How Users Force Refresh

#### In the UI

1. **Checkbox in Form**: A "🔄 Force refresh" checkbox appears at the top of the form, right after the submit/reset buttons
2. **User Action**: User checks the box before clicking "Find Resources"
3. **Result**: The system bypasses all cache lookups and runs a fresh search

**Visual Indicator**:
- **Label**: "🔄 Force refresh (bypass cache and get fresh results)"
- **Hint**: Explains that this may take longer but ensures up-to-date results
- **Styling**: Light purple background to make it stand out

#### Programmatic Usage

```python
# Force refresh - bypasses cache entirely
cached_results = get_cached_analysis(
    inputs, 
    cache_type="analysis",
    force_refresh=True  # Always returns None
)

# Useful for:
# - User explicitly requests fresh results
# - Testing new agent/task configurations
# - Debugging cache issues
# - After major course page updates
```

### Implementation Details

#### Frontend (`CourseForm.jsx`)

```jsx
// Checkbox in form
<input
  type="checkbox"
  id="force_refresh"
  name="force_refresh"
  checked={formData.force_refresh}
  onChange={handleChange}
/>
```

#### Backend Flow

1. **API Request** (`backend/models.py`):
   ```python
   force_refresh: Optional[bool] = Field(False, description="Force refresh - bypass cache")
   ```

2. **Job Submission** (`backend/main.py`):
   ```python
   force_refresh = inputs.pop('force_refresh', False)
   run_crew_async(job_id, inputs, force_refresh=force_refresh)
   ```

3. **Crew Execution** (`backend/crew_runner.py`):
   ```python
   async def _run_crew_worker(job_id: str, inputs: Dict[str, str], force_refresh: bool = False):
       # When cache is integrated:
       cached_results = get_cached_analysis(
           normalized_inputs, 
           cache_type="analysis",
           force_refresh=force_refresh  # Bypasses cache if True
       )
       if cached_results and not force_refresh:
           # Use cached results
           textbook_info = cached_results.get("textbook_info")
           topics = cached_results.get("topics")
       else:
           # Run fresh analysis
           # ... run crew ...
           # Cache results
           set_cached_analysis(normalized_inputs, results, cache_type="analysis")
   ```

### User Experience

#### Default Behavior (Force Refresh Unchecked)
- ✅ Fast: Uses cache if available
- ✅ Efficient: Saves API calls
- ⚠️ May return cached results (up to 7-30 days old depending on cache type)

#### Force Refresh (Checked)
- ✅ Fresh: Always gets latest results
- ✅ Up-to-date: Finds newly published resources
- ⚠️ Slower: Takes longer (no cache benefit)
- ⚠️ More expensive: Uses more API calls

### When to Use Force Refresh

**Recommended**:
- First time searching a course (no cache exists anyway)
- After course pages have been updated
- When you suspect new resources were published
- Testing new agent configurations

**Not Recommended**:
- Repeated searches of the same course (use cache)
- When you're satisfied with previous results
- During development/testing (unless testing cache behavior)

### Technical Notes

- `force_refresh` is **not stored** in the job inputs (removed before saving to DB)
- `force_refresh` is passed separately to `run_crew_async()`
- Default value is `False` (normal caching behavior)
- The checkbox state is reset when the form is reset

## Cache Management

### Manual Cache Operations

```python
from backend.cache import (
    get_cached_analysis,
    set_cached_analysis,
    clear_cache_for_config_change,
    get_cache_stats
)

# Get cache statistics
stats = get_cache_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Valid entries: {stats['valid_entries']}")
print(f"Stale entries: {stats['stale_entries']}")
print(f"Config hash: {stats['config_hash']}")

# Clear stale cache entries (from old config versions)
deleted = clear_cache_for_config_change()
print(f"Deleted {deleted} stale entries")
```

### Automatic Invalidation

The cache automatically invalidates when:

1. **Config Files Change**: Hash of `agents.yaml` or `tasks.yaml` changes
   - Old cache entries are ignored (different hash)
   - New cache entries use new hash
   - Stale entries can be cleaned up with `clear_cache_for_config_change()`

2. **TTL Expires**: Cache entry is older than configured TTL
   - Entry is deleted on next lookup
   - Fresh results are fetched and cached

3. **Force Refresh**: User explicitly bypasses cache
   - Returns None, forces fresh fetch

4. **Inputs Change**: Different course_url, book info, topics, or resource types

## Testing

Test the cache system:

```python
# Test cache hit
inputs1 = {"course_url": "https://example.com/course"}
results1 = get_cached_analysis(inputs1, cache_type="analysis")  # None (first time)

# Store in cache
set_cached_analysis(inputs1, {"textbook_title": "Test Book"}, cache_type="analysis")

# Test cache hit
results2 = get_cached_analysis(inputs1, cache_type="analysis")  # {"textbook_title": "Test Book"}

# Test force refresh
results3 = get_cached_analysis(
    inputs1, 
    cache_type="analysis", 
    force_refresh=True
)  # None (bypassed)

# Test config invalidation
# 1. Modify agents.yaml or tasks.yaml
# 2. Check cache again - should return None (invalidated)
results4 = get_cached_analysis(inputs1, cache_type="analysis")  # None (config changed)
```

## Guarantees

✅ **Config changes are detected**: Hash includes both config files  
✅ **Automatic invalidation**: Old cache entries are ignored when config changes  
✅ **No manual versioning**: No need to update version numbers  
✅ **Fast lookups**: Hash computation is cached in memory  
✅ **Safe fallback**: If cache fails, system continues normally  
✅ **Fresh data handling**: Two-tier TTL strategy ensures new resources are found

## Limitations

- Cache is based on exact input matching (course_url, book info, topics, etc.)
- Config hash is computed on each lookup (minimal overhead, ~1ms)
- Cache entries with different config hashes are not automatically deleted (use `clear_cache_for_config_change()` for cleanup)
- Full results caching may return stale data if new resources are published (use shorter TTL or cache analysis only)

## Summary

| Cache Type | TTL | Why | When to Use |
|------------|-----|-----|-------------|
| **Course Analysis** | 30 days | Expensive, changes rarely | Always (recommended) |
| **Full Results** | 7 days | New resources published | Only if you accept stale results |
| **Force Refresh** | N/A | Bypass cache | User requests fresh data |

**Best Practice**: Cache course analysis (30 days), always run resource discovery fresh. This gives you fast parsing with fresh results.

