# Environment Configuration

## Overview

The ScholarSource backend uses a centralized environment loading system that automatically loads the correct `.env` file based on the `ENVIRONMENT` variable.

## How It Works

### Environment Files

The system supports multiple environment files:

- `.env.local` - Local development (default)
- `.env.dev` - Development/staging environment
- `.env.prod` - Production environment
- `.env` - Fallback for any missing variables

### Priority Order

Environment variables are loaded with the following priority (highest to lowest):

1. **Already set environment variables** - Variables set in your shell/system
2. **Environment-specific file** - Based on `ENVIRONMENT` variable
3. **Base .env file** - Fallback for common variables

### ENVIRONMENT Variable

Set the `ENVIRONMENT` variable to control which config file is loaded:

```bash
# Local development (default)
ENVIRONMENT=local

# Development/staging
ENVIRONMENT=dev

# Production
ENVIRONMENT=prod
```

If `ENVIRONMENT` is not set, it defaults to `"local"`.

## Usage

### In Backend Code

All backend modules now use the centralized loader:

```python
from backend.env_loader import load_environment

# Load environment variables
load_environment()

# Now you can access environment variables
import os
db_url = os.getenv("DATABASE_URL")
```

### Module Auto-Loading

The `env_loader` module automatically loads environment variables when imported, so most modules don't need to call `load_environment()` explicitly if another module has already imported it.

## Files Updated

The following backend files now use the centralized loader:

- `backend/env_loader.py` - New centralized loader
- `backend/auth.py`
- `backend/main.py`
- `backend/database.py`
- `backend/email_service.py`
- `backend/celery_app.py`
- `backend/rate_limiter.py`
- `backend/tasks.py`
- `scripts/test.py`

## Configuration Example

### .env.local (Local Development)
```bash
ENVIRONMENT=local
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-local-anon-key
SUPABASE_JWT_SECRET=your-local-jwt-secret
OPENAI_API_KEY=sk-your-key
```

### .env.prod (Production)
```bash
ENVIRONMENT=prod
SUPABASE_URL=https://your-prod-project.supabase.co
SUPABASE_ANON_KEY=your-prod-anon-key
SUPABASE_JWT_SECRET=your-prod-jwt-secret
OPENAI_API_KEY=sk-your-prod-key
REDIS_URL=rediss://your-prod-redis-url
```

## Migration Notes

### Before
```python
from dotenv import load_dotenv
load_dotenv('.env.local')
load_dotenv()
```

### After
```python
from backend.env_loader import load_environment
load_environment()
```

## Benefits

1. **Consistency** - All modules load environment variables the same way
2. **Flexibility** - Easy to switch between environments
3. **Explicit** - Clear which environment file is being used
4. **Maintainable** - Single place to update loading logic
5. **Environment-aware** - Automatic selection based on ENVIRONMENT variable
