"""
Course Analysis Cache with Config-Based Invalidation

Caches course analysis results (textbook info, topics) to avoid re-running
expensive CrewAI operations for the same course URLs.

Cache keys include a hash of agents.yaml and tasks.yaml to ensure cache
invalidation when agent/task configurations change.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from backend.database import get_supabase_client

# Path to config files (relative to project root)
CONFIG_DIR = Path(__file__).parent.parent / "src" / "scholar_source" / "config"
AGENTS_CONFIG_PATH = CONFIG_DIR / "agents.yaml"
TASKS_CONFIG_PATH = CONFIG_DIR / "tasks.yaml"


# Separate TTL for course analysis vs full results
# Course analysis (textbook extraction, topics) changes less frequently
COURSE_ANALYSIS_TTL_DAYS = int(os.getenv('COURSE_ANALYSIS_TTL_DAYS', '30'))  # Default: 30 days
# Full resource discovery results change more frequently (new resources published)
RESOURCE_RESULTS_TTL_DAYS = int(os.getenv('RESOURCE_RESULTS_TTL_DAYS', '7'))  # Default: 7 days


def _compute_config_hash() -> str:
    """
    Compute a hash of agents.yaml and tasks.yaml files.
    
    This hash is included in cache keys to ensure cache invalidation
    when agent or task configurations change.
    
    Returns:
        str: SHA256 hash of both config files
    """
    hash_obj = hashlib.sha256()
    
    # Hash agents.yaml
    if AGENTS_CONFIG_PATH.exists():
        with open(AGENTS_CONFIG_PATH, 'rb') as f:
            hash_obj.update(f.read())
    else:
        hash_obj.update(b"agents.yaml_not_found")
    
    # Hash tasks.yaml
    if TASKS_CONFIG_PATH.exists():
        with open(TASKS_CONFIG_PATH, 'rb') as f:
            hash_obj.update(f.read())
    else:
        hash_obj.update(b"tasks.yaml_not_found")
    
    return hash_obj.hexdigest()[:16]  # Use first 16 chars for shorter keys


def _generate_cache_key(inputs: Dict[str, Any], config_hash: str) -> str:
    """
    Generate a cache key from inputs and config hash.
    
    The cache key is based on:
    - course_url (primary identifier)
    - book_url (if provided)
    - book_title + book_author (if provided)
    - isbn (if provided)
    - topics_list (if provided)
    - desired_resource_types (if provided)
    - config_hash (ensures invalidation on config changes)
    
    Args:
        inputs: Course input parameters
        config_hash: Hash of config files
        
    Returns:
        str: Cache key string
    """
    # Build key components
    key_parts = []
    
    # Primary identifiers
    if inputs.get('course_url'):
        key_parts.append(f"course:{inputs['course_url']}")
    if inputs.get('book_url'):
        key_parts.append(f"book_url:{inputs['book_url']}")
    if inputs.get('book_title') and inputs.get('book_author'):
        key_parts.append(f"book:{inputs['book_title']}|{inputs['book_author']}")
    if inputs.get('isbn'):
        key_parts.append(f"isbn:{inputs['isbn']}")
    
    # Optional parameters that affect results
    if inputs.get('topics_list'):
        # Normalize topics list (sort for consistent hashing)
        topics = sorted([t.strip() for t in str(inputs['topics_list']).split(',') if t.strip()])
        key_parts.append(f"topics:{','.join(topics)}")
    
    if inputs.get('desired_resource_types'):
        # Normalize resource types (sort for consistent hashing)
        resource_types = sorted([rt.strip() for rt in inputs['desired_resource_types'] if rt.strip()])
        if resource_types:
            key_parts.append(f"resources:{','.join(resource_types)}")
    
    # Include config hash to invalidate on config changes
    key_parts.append(f"config:{config_hash}")
    
    # Create final key
    key_string = "|".join(key_parts)
    
    # Hash the key string to keep it manageable
    return hashlib.sha256(key_string.encode()).hexdigest()


def get_cached_analysis(
    inputs: Dict[str, Any], 
    cache_type: str = "analysis",
    force_refresh: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Check cache for existing course analysis results.
    
    Returns cached results if:
    1. Cache entry exists for the given inputs
    2. Config hash matches current config files (ensures cache is valid)
    3. Cache entry hasn't expired (if TTL is set)
    4. force_refresh is False
    
    Args:
        inputs: Course input parameters
        cache_type: Type of cache entry ("analysis" for course analysis only, 
                   "full" for complete results including resources)
        force_refresh: If True, bypass cache and return None
        
    Returns:
        dict | None: Cached results (textbook_info, topics, etc.) or None if not found
    """
    # Force refresh bypasses cache
    if force_refresh:
        return None
    
    try:
        supabase = get_supabase_client()
        
        # Compute current config hash
        current_config_hash = _compute_config_hash()
        
        # Generate cache key (include cache_type in key to separate analysis vs full results)
        cache_key_base = _generate_cache_key(inputs, current_config_hash)
        cache_key = f"{cache_type}:{cache_key_base}"
        
        # Query cache table
        response = supabase.table("course_cache").select("*").eq("cache_key", cache_key).execute()

        if not response.data:
            return None

        cache_entry = response.data[0]

        # Check expiration based on cache type
        ttl_days = COURSE_ANALYSIS_TTL_DAYS if cache_type == "analysis" else RESOURCE_RESULTS_TTL_DAYS
        if ttl_days:
            cached_at = datetime.fromisoformat(cache_entry["cached_at"].replace('Z', '+00:00'))
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=datetime.utcnow().tzinfo)

            age = datetime.utcnow() - cached_at.replace(tzinfo=None)
            if age > timedelta(days=ttl_days):
                # Cache expired, delete entry
                supabase.table("course_cache").delete().eq("cache_key", cache_key).execute()
                return None

        # Verify config hash matches (double-check)
        if cache_entry.get("config_hash") != current_config_hash:
            # Config changed, invalidate this cache entry
            supabase.table("course_cache").delete().eq("cache_key", cache_key).execute()
            return None

        # Return cached results
        return cache_entry.get("results")
        
    except Exception as e:
        # If cache lookup fails, continue (don't break the app)
        logger.warning(f"Cache lookup failed: {str(e)}")
        return None


def set_cached_analysis(
    inputs: Dict[str, Any], 
    results: Dict[str, Any],
    cache_type: str = "analysis"
) -> None:
    """
    Store course analysis results in cache.
    
    Args:
        inputs: Course input parameters
        results: Analysis results to cache (textbook_info, topics, etc.)
        cache_type: Type of cache entry ("analysis" for course analysis only,
                   "full" for complete results including resources)
    """
    try:
        supabase = get_supabase_client()
        
        # Compute current config hash
        current_config_hash = _compute_config_hash()
        
        # Generate cache key (include cache_type in key)
        cache_key_base = _generate_cache_key(inputs, current_config_hash)
        cache_key = f"{cache_type}:{cache_key_base}"
        
        # Store in cache
        cache_data = {
            "cache_key": cache_key,
            "config_hash": current_config_hash,
            "cache_type": cache_type,  # Store type for filtering/debugging
            "inputs": inputs,  # Store inputs for debugging/auditing
            "results": results,
            "cached_at": datetime.utcnow().isoformat()
        }
        
        # Upsert (insert or update if exists)
        supabase.table("course_cache").upsert(
            cache_data,
            on_conflict="cache_key"
        ).execute()

    except Exception as e:
        # If cache storage fails, continue (don't break the app)
        logger.error(f"Cache storage failed: {str(e)}")


def clear_cache_for_config_change() -> int:
    """
    Clear all cache entries when config files change.
    
    This is called automatically when config hash changes, but can also
    be called manually if needed.
    
    Returns:
        int: Number of cache entries deleted
    """
    try:
        supabase = get_supabase_client()
        
        # Get current config hash
        current_config_hash = _compute_config_hash()
        
        # Delete all entries with different config hash
        response = supabase.table("course_cache").select("cache_key").neq("config_hash", current_config_hash).execute()
        
        deleted_count = 0
        if response.data:
            for entry in response.data:
                supabase.table("course_cache").delete().eq("cache_key", entry["cache_key"]).execute()
                deleted_count += 1
        
        return deleted_count
        
    except Exception as e:
        logger.warning(f"Cache cleanup failed: {str(e)}")
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics (for monitoring/debugging).
    
    Returns:
        dict: Cache statistics
    """
    try:
        supabase = get_supabase_client()
        
        # Get current config hash
        current_config_hash = _compute_config_hash()
        
        # Count total entries
        total_response = supabase.table("course_cache").select("cache_key", count="exact").execute()
        total_count = total_response.count if hasattr(total_response, 'count') else 0
        
        # Count entries with current config hash
        valid_response = supabase.table("course_cache").select("cache_key", count="exact").eq("config_hash", current_config_hash).execute()
        valid_count = valid_response.count if hasattr(valid_response, 'count') else 0
        
        return {
            "total_entries": total_count,
            "valid_entries": valid_count,
            "stale_entries": total_count - valid_count,
            "config_hash": current_config_hash
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "config_hash": _compute_config_hash()
        }

