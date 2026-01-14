# ScholarSource Deployment Plan

This document provides step-by-step instructions for deploying ScholarSource to production.

---

## 📋 Deployment Overview

**Architecture:**
- **Frontend**: React/Vite app on Cloudflare Pages (Free)
- **Backend**: FastAPI on Railway ($5/month)
- **Database**: Supabase PostgreSQL (Free tier / $25/month Pro)

**Total Monthly Cost:** $5-$30/month depending on usage

---

## ✅ Pre-Deployment Checklist

Before deploying, ensure you have:

- [✅] Git repository with all code committed
- [✅] OpenAI API key with Tier 2+ rate limits (450k TPM)
- [✅] Serper API key for web search
- [✅] Supabase account created
- [✅] Railway account created (free to sign up)
- [✅] Cloudflare account created (free to sign up)
- [✅] Domain name (optional, but recommended for production)

---

## Part 1: Database Setup (Supabase)

### [✅] 1.1 Create Supabase Project

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in project details:
   - **Name**: `scholar-source-prod`
   - **Database Password**: Generate strong password (save in password manager!)
   - **Region**: Choose closest to your users (e.g., US East, EU West)
4. Click **"Create new project"** (takes ~2 minutes)

### [✅] 1.2 Create Database Schema

1. In Supabase Dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Paste the following SQL:
 - supabase_schema.sql

4. Click **"Run"** to execute

### [✅] 1.3 Get Supabase Credentials

1. In Supabase Dashboard, go to **Project Settings** → **API**
2. Copy and save these values:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon/public key** (long string starting with `eyJ...`)
   - **service_role key** (under "Service role" section - keep this secret!)

3. Go to **Project Settings** → **API** → Scroll down to **JWT Settings**
4. Copy and save:
   - **JWT Secret** (used for backend JWT verification - CRITICAL for authentication)

**Important:** Never commit these credentials to version control. Use environment variables only.

**Status:** ✅ Database configured with authentication ready

---

## Part 2: Backend Deployment (Railway)

### 2.1 Prepare Backend for Deployment

1. [✅] **Create `railway.json files for Celery and backend` :**

1. Create railway.backend.json with contents:
```{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "RAILPACK" },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port \"$PORT\" --log-level info"
  }
}```
2. Create railway.celery.json with contents.
```{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "RAILPACK" },
  "deploy": {
    "startCommand": "python -u -m celery -A backend.celery_app worker --loglevel=info --queues=crew_jobs,default --concurrency=2 --max-tasks-per-child=50 --time-limit=1800 --soft-time-limit=1500 --pool=prefork"
  }
}``

2. **Update `pyproject.toml` to ensure all dependencies are listed:**

```toml
[project]
name = "scholar-source"
version = "0.1.0"
requires-python = ">=3.10,<3.13"

dependencies = [
    "crewai[tools]>=0.120.1,<1.0.0",
    "lancedb<0.26",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",
    "pydantic>=2.0.0",
    "supabase>=2.0.0",
    "python-dotenv>=1.0.0",
]
```
3. **Update `requirements.txt` for railway:**
Railway needed a requirements.txt so you have to run
```uv pip compile pyproject.toml -o requirements.txt```

4. **Update CORS origins in `backend/main.py`:**

```python
# Update to include your production frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://https://scholar-source.pages.dev/",  # Cloudflare Pages (temp URL)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### [✅] 2.2 Create Redis Database in Redis Cloud (Required for Scaling)
1. *[✅] *Sign up for Redis Cloud** (if not already done):
   - Go to https://redis.com/try-free/
   - Create account and verify email
   - Select "Fixed plan" → "Free" (30MB, perfect for getting started)

2. [✅] **Create Redis Database:**
   - Click "New database"
   - Name: `scholarsource-queue`
   - Region: Choose closest to your Railway deployment region
   - Click "Activate"

3. [✅] **Get Redis Connection URL:**
   - Go to database configuration
   - Copy the "Public endpoint" connection string
   - Format: `redis://default:PASSWORD@HOST:PORT`
   - **Save this URL** - you'll need it for Railway environment variables

### [✅] 2.3 Create Railway Deployment for Backend

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub account
5. Select your `scholar_source` repository
6. Railway will auto-detect Python and start building


###  [✅] 2.4 Railway Configure

#### [✅] 2.4.1 Railway Configure Environment Variables

1. In Railway dashboard, click on your deployed service
2. Go to **"Variables"** tab
3. Add the following environment variables:
NOTE: You can go to the project root and add shared variables. BUT you
must remember to go to the actual service->variables->shared, and add any specific ones you need.

```bash
# API Keys
OPENAI_API_KEY=sk-proj-...your_key_here
SERPER_API_KEY=...your_serper_key_here

# Database & Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
SUPABASE_JWT_SECRET=your_jwt_secret_here  # CRITICAL: Required for JWT verification

# Redis (Required for task queue and rate limiting)
REDIS_URL=redis://default:PASSWORD@HOST:PORT

RESEND_API_KEY=re_your_resend_api_key_here

# From Email Address (optional - for email notifications)
RESEND_FROM_EMAIL=noreply@scholarshipmanage.com

MAX_CREW_ITERATIONS=10

COURSE_INTELLIGENCE_AGENT_MODEL=openai/gpt-4o
RESOURCE_DISCOVERY_AGENT_MODEL=openai/gpt-4o-mini
RESOURCE_VALIDATOR_AGENT_MODEL=openai/gpt-4o-mini
OUTPUT_FORMATTER_AGENT_MODEL=openai/gpt-4o-mini

# For caching
COURSE_ANALYSIS_TTL_DAYS=30
RESOURCE_RESULTS_TTL_DAYS=7

REDIS_URL=redis://localhost:6379/0

#How to time out if job hasn't completed by
VITE_SEARCH_TIMEOUT_MINUTES=20

LOG_LEVEL=INFO
```

####  [✅] 2.4.2 Set Railway configuration file for backend service
1. Click on your Railway API Service
2. Go to Settings->Config-as-Code
3. Select the railway.backend.json file
4. Deploy changes

####  [✅] 2.4.3 Other Backend configuration
1. [✅] **Set up custom domain (optional):**
   - Go to **"Settings"** → **"Domains"**
   - Add custom domain (e.g., `api.yourdomain.com`)
   - Update your DNS records as instructed

2. [✅] **Configure health checks:**
   - Go to **"Settings"** → **"Health Checks"**
   - Set health check path: `/api/health`
   - Set timeout: 30 seconds

3. [✅] **Enable always-on service:**
   - Go to **"Settings"** → **"Service"**
   - Ensure service is on **"Always On"** plan ($5/month)
   - This prevents cold starts and ensures 24/7 availability

4. **Configure resource limits (optional):**
   - Go to **"Settings"** → **"Resources"**
   - Set memory limit: 512MB-1GB (should be sufficient)
   - Set CPU limit: 1-2 vCPUs
   NOTE: FREE VERSION ONLY LETS YOU GET 8MB MAX

###  [✅] 2.5 Create Railway Redis Service
1. From Railway Dashboard, click on your project
2. Press the Create button
3. Select the Redis Template
4. Deploy the changes

### [✅] 2.6 Configure Railway Service

1. [✅] **Set up custom domain (optional):**
   - Go to **"Settings"** → **"Domains"**
   - Add custom domain (e.g., `api.yourdomain.com`)
   - Update your DNS records as instructed

2. [✅] **Configure health checks:**
   - Go to **"Settings"** → **"Health Checks"**
   - Set health check path: `/api/health`
   - Set timeout: 30 seconds

3. [✅] **Enable always-on service:**
   - Go to **"Settings"** → **"Service"**
   - Ensure service is on **"Always On"** plan ($5/month)
   - This prevents cold starts and ensures 24/7 availability

4. **Configure resource limits (optional):**
   - Go to **"Settings"** → **"Resources"**
   - Set memory limit: 512MB-1GB (should be sufficient)
   - Set CPU limit: 1-2 vCPUs
   NOTE: FREE VERSION ONLY LETS YOU GET 8MB MAX


### [✅] 2.7 Create Railway Celery Broker
1. Make sure Celery instance references REDIS_URL in celery_app.py
2. From Railway Dashboard, click on your project
3. Press the Create button
4. Select Github Repo as the template
5. Select the scholar_source repo
6. Go to Settings->Config-as-Code
7. Select the railway.celery.json file
10. Deploy changes

NOTE: YOU'LL NEED TO SET THE APPROPRIATE USER PRIVELGES FOR THE CONTAINER 
You will see this warning in the Railway celery log files. 
"SecurityWarning: You're running the worker with superuser privileges: this is
absolutely not recommended!"
For a small internal app, this warning is usually acceptable during development. To harden later, you would:
 1. Create a non‑root user in the image (or use a base image that does), and
 2. Start Celery with --uid / --gid for that user, or set the container user in your Dockerfile or service config.
​


### 2.8 Railway Environment Management

Railway supports multiple environments (production, development, staging) for managing different deployments.

#### Environment Detection

Railway automatically sets these environment variables:
- `RAILWAY_ENVIRONMENT_NAME` - Environment name (production, development, etc.)
- `RAILWAY_GIT_BRANCH` - Git branch deployed (main, develop, etc.)
- `RAILWAY_GIT_COMMIT_SHA` - Full commit hash
- `RAILWAY_SERVICE_NAME` - Service name (web, worker)
- `RAILWAY_PROJECT_NAME` - Project name

#### Setting Up Multiple Environments

**Method 1: Branch-Based (Recommended)**
- Production: Deploy from `main` branch → `production` environment
- Development: Deploy from `develop` branch → `development` environment

**Method 2: Manual Environment Creation**
1. Railway Dashboard → Your Project
2. Click "New Environment" (top right)
3. Name it (e.g., `staging`, `testing`)
4. Configure separate environment variables per environment

#### Environment-Specific Configuration

Set different variables per environment in Railway Dashboard:
- Select environment from dropdown (top-left)
- Go to Variables tab
- Add environment-specific values

**Example:**
- Production: `LOG_LEVEL=INFO`, `REDIS_URL=redis://prod-redis...`
- Development: `LOG_LEVEL=DEBUG`, `REDIS_URL=redis://dev-redis...`

#### Checking Current Environment

**In Railway Dashboard:**
- Look at top-left breadcrumb: `[Project] > [Environment] > [Service]`

**In Code:**
```python
import os
railway_env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "local")
logger.info(f"Running in {railway_env} environment")
```

**Via Railway CLI:**
```bash
railway status  # Shows current environment
railway environment production  # Switch to production
railway environment development  # Switch to development
```

### 2.9 Configure Scaling (Optional)

**Scale the Worker Process:**

By default, Railway runs 1 instance of each process. To scale:

1. Go to your service settings
2. Click on "Settings" tab
3. Under "Replicas", you can set:
   - **Horizontal scaling:** Number of instances (costs more)
   - **Vertical scaling:** CPU/Memory per instance

**Recommended Starter Configuration:**
- **Web instances:** 1 (scale up if API becomes slow)
- **Worker instances:** 1-2 (scale based on queue depth)
- **Memory:** 512MB - 1GB per instance
- **CPU:** Shared (upgrade to dedicated if needed)

**Auto-scaling (Pro plan):**
- Railway Pro supports auto-scaling based on CPU/memory
- Configure min/max instances
- Automatically scales workers based on load

### 2.10 Verify Backend Deployment

1. Copy your Railway deployment URL (e.g., `https://scholarsource-dev.up.railway.app`)
2. **Test the health endpoint (no auth required):**

```bash
curl https://scholarsource-dev.up.railway.app/api/health
```

**Expected response:**
```json
{"status": "healthy", "database": "connected", "version": "0.1.0"}
```

3. **Verify Authentication is Required:**

   Try to submit a job without authentication (should fail):
   ```bash
   curl -X POST https://scholarsource-dev.up.railway.app/api/submit \
     -H "Content-Type: application/json" \
     -d '{
       "course_name": "Test Course",
       "university_name": "Test University",
       "book_title": "Test Book",
       "book_author": "Test Author"
     }'
   ```

   **Expected response (401 Unauthorized):**
   ```json
   {"error": "Missing Authorization header"}
   ```

4. **Create Test User in Supabase:**

   - Go to Supabase Dashboard → Authentication → Users
   - Click **"Add user"** → **"Create new user"**
   - Enter email: `test@yourdomain.com`
   - Set password (save it!)
   - Click **"Create user"**

5. **Get JWT Token for Testing:**

   You can obtain a JWT token by:
   - Using the frontend login form (preferred)
   - Or using Supabase Auth API directly:

   ```bash
   curl -X POST 'https://YOUR_SUPABASE_URL/auth/v1/token?grant_type=password' \
     -H "apikey: YOUR_SUPABASE_ANON_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@yourdomain.com",
       "password": "your-password"
     }'
   ```

   Save the `access_token` from the response.

6. **Submit Test Job (with authentication):**
   ```bash
   curl -X POST https://scholarsource-dev.up.railway.app/api/submit \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{
       "course_name": "Test Course",
       "university_name": "Test University",
       "book_title": "Test Book",
       "book_author": "Test Author"
     }'
   ```

   **Expected response:**
   ```json
   {
     "job_id": "uuid-here",
     "status": "pending",
     "message": "Job created successfully"
   }
   ```

7. **Check Job Status (with authentication):**
   ```bash
   curl https://scholarsource-dev.up.railway.app/api/status/{job_id} \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

   **Expected:** Returns job status (`pending`, `running`, `completed`, or `failed`)

5. **Monitor Worker Logs:**
   - Go to Railway dashboard → Deployments → Latest
   - Filter logs by `worker` process
   - You should see Celery processing the job

**Check Redis Connection:**

In Railway logs, verify:
- ✅ No Redis connection errors
- ✅ Worker successfully connected to Redis
- ✅ Tasks are being enqueued and consumed

**Status:** ✅ Backend deployed and running on Railway

---

## Part 3: Frontend Deployment (Cloudflare Pages)

### 3.1 Prepare Frontend for Deployment

1. **Update `web/.env.production` (create if doesn't exist):**

```bash
VITE_API_URL=https://scholarsource-dev.up.railway.app
```

2. **Update `web/vite.config.js` for production:**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable for production
  }
})
```

3. **Test production build locally:**

```bash
cd web
npm run build
npm run preview
```

### [✅] 3.2 Deploy to Cloudflare Pages

1. Go to https://dash.cloudflare.com
2. Navigate to **"Workers & Pages"**
3. Click **"Create application"** → **"Pages"** → **"Connect to Git"**
4. Authorize Cloudflare to access your GitHub account
5. Select your `scholar_source` repository

### 3.3[✅] Configure Build Settings

1. **Framework preset**: Select **"Vite"** (or None)
2. **Build command**:
   ```bash
   cd web && npm install && npm run build
   ```
3. **Build output directory**:
   ```
   web/dist
   ```
4. **Root directory**: Leave empty (or set to `/`)

### 3.4 [✅] Add Environment Variables

1. Click **"Environment variables"**
2. Add the following:

```bash
# Backend API URL
VITE_API_URL=https://scholarsource-dev-app.up.railway.app

# Supabase Configuration (for frontend authentication)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGc...your_anon_key_here
```

**Important:** Use the same Supabase URL and anon key from Part 1.3

3. Select **"Production"** environment
4. Click **"Save"**

### [✅] 3.5 Deploy

1. Click **"Save and Deploy"**
2. Wait for build to complete (~2-5 minutes)
3. Cloudflare will provide a temporary URL: `https://scholar_source.pages.dev`

### 3.6 Configure Custom Domain (Optional)

1. Go to **"Custom domains"** tab
2. Click **"Set up a custom domain"**
3. Enter your domain (e.g., `app.yourdomain.com` or `yourdomain.com`)
4. Follow DNS configuration instructions
5. Wait for SSL certificate to provision (~5-10 minutes)

### [✅]3.7 Verify Frontend Deployment

1. Visit your Cloudflare Pages URL: `https://scholar_source.pages.dev`

2. **Test Authentication Flow:**
   - Verify you see the login/signup page on first visit
   - Click "Sign Up" tab
   - Create a new account with email and password
   - Verify you're redirected to the main app after signup
   - Log out using the user menu
   - Log back in with the same credentials
   - Verify session persists on page reload

3. **Test Authenticated Form Submission:**
   - Fill in course information (e.g., "Introduction to Computer Science")
   - Submit the form
   - Verify job status updates appear (pending → running → completed)
   - Wait for job to complete (~2-5 minutes)
   - Verify results display correctly with resource links

4. **Test User Isolation:**
   - Note your job ID
   - Log out
   - Create a different test account
   - Verify you cannot see jobs from the first account

5. **Test UI Features:**
   - Test copy to clipboard buttons
   - Test export to different formats
   - Test responsive design on mobile/tablet

**Status:** ✅ Frontend deployed with authentication working on Cloudflare Pages

---

## Part 4: Post-Deployment Configuration

### [✅] 4.1 Update Backend CORS

Now that you have the production frontend URL, update the backend CORS configuration:

1. [✅] Edit `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://scholar_source.pages.dev",  # Cloudflare Pages
        "https://yourdomain.com",  # Custom domain
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)
```

3. Railway will auto-deploy the update (~1-2 minutes)

### [ ] 4.2 Set Up Monitoring

#### 4.2.1 Railway (Backend Monitoring)

1. Go to Railway dashboard → **"Observability"**
2. Enable metrics collection (Enabled by default). But you can't see alerts unless you're on the pro plan.
3. Set up alerts for:
   - High error rates (>5% of requests)
   - High memory usage (>80%)
   - Service downtime

#### 4.2.2 Supabase (Database Monitoring)

1. Go to Supabase dashboard → **"Reports"**
2. Monitor:
   - Database size (stay under 500MB for free tier)
   - API requests (stay under limits)
   - Active connections

#### 4.2.3 Cloudflare (Frontend Monitoring)

1. Go to Cloudflare dashboard → **"Analytics"**
2. Monitor:
   - Page views
   - Bandwidth usage (unlimited on free tier)
   - Error rates

### 4.3 Configure Backups

#### [ ] Supabase Database Backups

1. Go to Supabase dashboard → **"Database"** → **"Backups"**
2. Verify automatic daily backups are enabled
3. Free tier: 7 days of backups
4. Pro tier: 30 days of backups + point-in-time recovery

**Manual backup (optional):**

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Backup database
supabase db dump -f backup_$(date +%Y%m%d).sql
```

---

## Part 5: Testing in Production

### 5.1 End-to-End Testing

Test the complete workflow in production:

1. **Test Authentication:**
   - Go to your production URL
   - Verify login/signup page appears for unauthenticated users
   - Create a new account (test@yourdomain.com)
   - Verify successful signup redirects to main app
   - Log out
   - Log back in with same credentials
   - Verify session persists on page reload

2. **Submit an authenticated job:**
   - Fill in course information (e.g., "MIT 6.006 Introduction to Algorithms")
   - Submit the form
   - Note the job ID returned

3. **Monitor job execution:**
   - Watch the loading status updates
   - Verify status polling works (every 2 seconds)
   - Wait for job completion (2-5 minutes)
   - Check Railway logs for worker activity

4. **Verify results:**
   - Check that results display correctly with resource cards
   - Verify resource titles, URLs, and descriptions render properly
   - Test "Copy" buttons for URLs
   - Test export functionality

5. **Test error handling:**
   - Submit form with malicious input (e.g., `<script>alert('XSS')</script>`) → should be rejected
   - Submit form with no inputs → should show validation error
   - Try to access another user's job → should return 403/404
   - Submit job with JavaScript URL → should be rejected
   - Test with expired/invalid JWT token → should return 401

### 5.2 Performance Testing

1. **Test concurrent users:**
   - Have 2-3 people submit jobs simultaneously
   - Verify all jobs complete successfully
   - Check Railway metrics for resource usage

2. **Test rate limits:**
   - Submit multiple jobs in quick succession
   - Monitor OpenAI API usage
   - Verify retry logic handles rate limits

3. **Test database persistence:**
   - Submit a job and get results
   - Restart Railway service

### 5.3 Security Testing

1. **Test Authentication & Authorization:**
   - Try API requests without JWT token → should return 401
   - Try with invalid/expired token → should return 401
   - Try to access another user's job → should return 403/404
   - Verify JWT signature validation is working

2. **Test Input Validation:**
   - Try prompt injection patterns (e.g., "Ignore previous instructions") → should be rejected
   - Try XSS payloads (`<script>alert('XSS')</script>`) → should be rejected
   - Try JavaScript/data URLs → should be rejected
   - Try malformed ISBNs → should be rejected
   - Try IP addresses in domain fields → should be rejected
   - Verify legitimate academic input passes validation

3. **Test CORS:**
   - Try accessing API from unauthorized origin → should be blocked
   - Verify only allowed origins can make requests

4. **Test SQL Injection Protection:**
   - Try SQL injection in form fields → should be safely handled by Supabase RLS
   - Verify Supabase Row-Level Security is active

5. **Test Rate Limiting:**
   - Submit many requests quickly → should be rate limited
   - Verify slowapi middleware is working

6. **Test Email Security:**
   - Submit job that completes successfully
   - Check received email for proper HTML escaping
   - Verify no script tags or malicious content in email

---

## Part 6: Going Live

### 6.1 Final Checklist

Before announcing to users:

- [ ] All environment variables set correctly
- [ ] CORS configured with production URLs
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificates active (automatic with Cloudflare/Railway)
- [ ] End-to-end testing passed
- [ ] Error tracking configured
- [ ] Monitoring dashboards set up
- [ ] Backup strategy in place
- [ ] Documentation updated with production URLs

### 6.2 Soft Launch

1. Share with 5-10 beta testers
2. Monitor error logs closely
3. Gather feedback on:
   - User experience
   - Resource quality
   - Performance issues
   - Bugs or errors

### 6.3 Full Launch

Once beta testing is successful:

1. Announce to target audience (students, educators)
2. Share production URL
3. Monitor usage metrics:
   - Jobs submitted per day
   - Completion rate
   - Error rate
   - User retention

---

## Part 7: Maintenance & Operations

### 7.1 Daily Operations

**Monitor (5-10 minutes/day):**
- Railway dashboard for backend errors
- Supabase dashboard for database usage
- Cloudflare analytics for frontend traffic

**Alert thresholds:**
- Backend error rate >5%
- Database size approaching limits
- OpenAI API costs exceeding budget

### 7.2 Weekly Maintenance

**Tasks (30 minutes/week):**
- Review error logs and fix critical issues
- Check database size and clean up old jobs if needed
- Review OpenAI API usage and costs
- Update dependencies if security patches available

### 7.3 Monthly Review

**Tasks (1-2 hours/month):**
- Analyze usage metrics and trends
- Review and optimize costs
- Plan feature improvements based on feedback
- Update documentation

### 7.4 Scaling Considerations

**When to upgrade:**

| Metric | Free/Starter | Upgrade Trigger | Recommended Action |
|--------|--------------|-----------------|-------------------|
| Database size | <500MB | >400MB | Upgrade Supabase to Pro ($25/mo) or implement job cleanup |
| API requests | <500K/month | >400K/month | Upgrade Supabase to Pro |
| Railway usage | $5/mo | Backend slow | Upgrade Railway plan or optimize code |
| OpenAI costs | Variable | >$100/mo | Review token usage, optimize prompts, or implement caching |
| Concurrent users | ~10 | >50 | Add Redis caching, optimize database queries |

---

## Part 8: Rollback Plan

If deployment fails or critical issues arise:

### 8.1 Backend Rollback

**Option 1: Railway rollback**
1. Go to Railway dashboard → **"Deployments"**
2. Find previous successful deployment
3. Click **"Redeploy"**

**Option 2: Git rollback**
```bash
git revert HEAD
git push origin main
# Railway auto-deploys
```

### 8.2 Frontend Rollback

**Option 1: Cloudflare Pages rollback**
1. Go to Cloudflare Pages dashboard → **"Deployments"**
2. Find previous deployment
3. Click **"Rollback"**

**Option 2: Git rollback**
```bash
git revert HEAD
git push origin main
# Cloudflare auto-deploys
```


## Part 9: Cost Optimization

### 9.1 Current Costs (MVP)

| Service | Plan | Cost/Month |
|---------|------|------------|
| Railway (Backend) | Starter | $5 |
| Supabase (Database) | Free | $0 |
| Cloudflare Pages (Frontend) | Free | $0 |
| OpenAI API | Usage-based | ~$10-50 |
| Serper API | Free tier | $0 |
| **Total** | | **$15-55/month** |

### 9.2 Cost Optimization Strategies

**Reduce OpenAI costs:**
- Use GPT-4o-mini for non-critical agents ✅ (already doing this)
- Implement response caching for repeated queries
- Optimize prompts to reduce token usage
- Set monthly spending limits in OpenAI dashboard

**Reduce database costs:**
- Implement job cleanup (delete jobs >30 days old)
- Optimize JSONB fields to reduce size

**Monitor and alert:**
- Set up billing alerts in OpenAI (e.g., alert at $50)
- Monitor Railway usage (alert if approaching next tier)
- Track Supabase database size (alert at 450MB)

---

## Part 11: Security Hardening (Production Checklist)

### 11.1 Environment Security

- [ ] All API keys stored in environment variables (never in code)
- [ ] `.env` file in `.gitignore` (verify with `git status`)
- [ ] Separate credentials for dev/staging/prod environments
- [ ] Rotate API keys quarterly

### 11.2 Database Security

- [ ] Row Level Security (RLS) enabled on Supabase
- [ ] Database credentials never exposed to frontend
- [ ] Regular backups configured
- [ ] SQL injection prevention (using Supabase client ✅)

### 11.3 API Security

- [✅] CORS restricted to known origins only
- [ ] Rate limiting implemented (add in Phase 2)
- [✅] Input validation on all endpoints
- [✅] HTTPS enforced (automatic with Railway/Cloudflare)

### 11.4 Frontend Security

- [ ] Content Security Policy (CSP) headers configured
- [✅] No sensitive data in localStorage
- [ ] XSS prevention (React handles this ✅)
- [✅] No API keys in frontend code

---

## Part 12: Success Metrics

Track these metrics to measure deployment success:

### Technical Metrics

- **Uptime**: Target >99% (use UptimeRobot or similar)
- **Error rate**: Target <2% of requests
- **Response time**: Target <2 seconds for API calls
- **Job completion rate**: Target >95% of jobs complete successfully
- **Job completion time**: Target 2-5 minutes per job

### Business Metrics

- **Daily active users**: Track growth over time
- **Jobs submitted per day**: Measure engagement
- **User retention**: % of users who return within 7 days

### Cost Metrics

- **Cost per job**: Total monthly costs ÷ jobs submitted
- **OpenAI cost per job**: OpenAI costs ÷ jobs submitted
- **Infrastructure cost per user**: Fixed costs ÷ monthly active users

---

## Part 10: Railway Deployment Troubleshooting

### 10.1 Common Deployment Issues

#### Issue 1: Worker Not Starting

**Symptoms:**
- Only see `web` process logs
- No Celery startup messages
- Jobs stay in `queued` status forever
- Worker exits immediately with no error

**Causes:**
- Procfile not detected or incorrect
- Worker process crashed during startup
- Missing dependencies
- Import errors
- PYTHONPATH not set correctly

**Fixes:**

1. **Verify Procfile exists and is correct:**
   ```bash
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT --log-level info
   worker: bash scripts/railway_worker_start.sh
   ```

2. **Check Railway deployment logs:**
   - Go to Railway Dashboard → Deployments → Latest
   - Look for worker process startup messages
   - Check for import errors or missing modules

3. **Verify dependencies:**
   - Ensure `celery[redis]>=5.3.0` and `redis>=5.0.0` in `requirements.txt`
   - Check Railway build logs show successful installation

4. **Test imports locally:**
   ```bash
   python -c "from backend.celery_app import app; print('✅ OK')"
   python -c "from backend.tasks import run_crew_task; print('✅ OK')"
   ```

5. **Use enhanced startup script:**
   The project includes `scripts/railway_worker_start.sh` which:
   - Sets PYTHONPATH correctly
   - Tests imports before starting
   - Verifies Redis connection
   - Provides detailed logging

#### Issue 2: Redis Connection Failed

**Symptoms:**
```
celery.exceptions.ImproperlyConfigured: CELERY_BROKER_URL is not set
```
or
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Fixes:**
1. Verify `REDIS_URL` environment variable is set
2. Check Redis Cloud database is active
3. Verify Redis URL format: `redis://default:PASSWORD@HOST:PORT`
4. Check Redis Cloud firewall allows Railway IPs (usually not an issue)
5. Test Redis connection:
   ```bash
   railway run python -c "from redis import Redis; r=Redis.from_url('$REDIS_URL'); print(r.ping())"
   ```

#### Issue 3: Environment Variables Not Loading

**Symptoms:**
- Missing API keys errors
- Database connection failed
- Application crashes on startup

**Fixes:**
1. Go to Railway Variables tab
2. Verify all required variables are set
3. Check for typos in variable names
4. Redeploy after adding variables (click "Deploy" → "Redeploy")

#### Issue 4: Port Binding Error

**Symptoms:**
```
Error binding to 0.0.0.0:8000
```

**Cause:**
- Using hardcoded port instead of `$PORT`

**Fix:**
- Procfile should use `$PORT`, not `8000`:
  ```
  web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```

#### Issue 5: Jobs Not Being Processed

**Symptoms:**
- Jobs stuck in `queued` status
- Worker logs show "ready" but no task execution
- Tasks not appearing in worker logs

**Fixes:**
1. **Check worker logs for errors:**
   - Railway Dashboard → Service Logs → Filter by `worker`
   - Look for task execution messages

2. **Verify queue names match:**
   - `backend/celery_app.py` defines queues (`crew_jobs`, `default`)
   - Procfile worker listens to correct queues: `--queues=crew_jobs,default`

3. **Check task registration:**
   ```python
   from backend.celery_app import app
   print(app.control.inspect().registered())  # Should show run_crew_task
   ```

4. **Manually test task:**
   ```python
   from backend.tasks import run_crew_task
   result = run_crew_task.delay("test-job-id", {"course_url": "https://example.com"})
   print(f"Task ID: {result.id}, Status: {result.status}")
   ```

5. **Verify worker is listening to correct queues:**
   ```python
   from backend.celery_app import app
   print(app.control.inspect().active_queues())  # Should show crew_jobs and default
   ```

#### Issue 6: Worker Dies Immediately

**Symptoms:**
- Worker starts but exits immediately
- No error messages in logs
- Process exits with code 1

**Fixes:**
1. **Check for syntax errors:**
   ```bash
   python -m py_compile backend/celery_app.py
   python -m py_compile backend/tasks.py
   ```

2. **Test imports:**
   ```bash
   python -c "import backend.celery_app"
   python -c "import backend.tasks"
   ```

3. **Check Railway build logs:**
   - Verify all dependencies installed successfully
   - Look for import errors during build

4. **Use startup script with diagnostics:**
   The `scripts/railway_worker_start.sh` script tests imports before starting

#### Issue 7: No Logs Visible

**Symptoms:**
- Worker process starts but produces no logs
- Cannot see what's happening

**Fixes:**
1. **Ensure unbuffered output:**
   - Use `PYTHONUNBUFFERED=1` in Procfile
   - Use `python -u` flag for unbuffered binary output
   - Use `--loglevel=info` or `--loglevel=debug`

2. **Check Railway log viewer:**
   - Go to Railway Dashboard → Service Logs (not just Deploy Logs)
   - Filter by `worker` process
   - Logs may take a few seconds to appear

3. **Verify logging configuration:**
   - Check `backend/logging_config.py` is configured correctly
   - Ensure handlers output to stdout/stderr

#### Issue 8: Pool/Concurrency Issues

**Symptoms:**
- Worker starts but tasks don't execute
- Worker hangs or becomes unresponsive
- High memory usage

**Fixes:**
1. **Use `solo` pool for Railway (recommended):**
   ```bash
   celery -A backend.celery_app worker --pool=solo --loglevel=info
   ```

2. **Adjust concurrency based on Railway plan:**
   - Hobby plan (512MB RAM): `--concurrency=1` or `--pool=solo`
   - Pro plan (8GB RAM): `--concurrency=2-4`

3. **Pool types:**
   - `solo` - Single process (best for Railway, recommended)
   - `prefork` - Multi-process (higher memory, default)
   - `threads` - Multi-threaded (lower memory)

### 10.2 Celery Worker Configuration

#### Recommended Worker Settings for Railway

**For Hobby Plan (512MB RAM):**
```bash
celery -A backend.celery_app worker \
  --pool=solo \
  --loglevel=info \
  --queues=crew_jobs,default \
  --max-tasks-per-child=50 \
  --time-limit=1800 \
  --soft-time-limit=1500
```

**For Pro Plan (8GB+ RAM):**
```bash
celery -A backend.celery_app worker \
  --pool=prefork \
  --concurrency=2 \
  --loglevel=info \
  --queues=crew_jobs,default \
  --max-tasks-per-child=50 \
  --time-limit=1800 \
  --soft-time-limit=1500
```

#### Worker Health Monitoring

The backend includes a worker health endpoint at `/api/health/workers`:

```bash
curl https://your-app.railway.app/api/health/workers
```

**Expected response:**
```json
{
  "status": "healthy",
  "workers_available": true,
  "worker_count": 1,
  "workers": ["celery@hostname"]
}
```

### 10.3 Useful Railway CLI Commands

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs (live)
railway logs

# View logs (worker only)
railway logs --filter worker

# Run command in Railway environment
railway run python scripts/test.py --redis

# SSH into Railway container (Pro plan)
railway shell
```

### 10.4 Monitoring and Maintenance

#### Monitoring Checklist

**Daily:**
- [ ] Check Railway dashboard for any crashed processes
- [ ] Monitor error rate in logs
- [ ] Check queue depth (jobs waiting to be processed)

**Weekly:**
- [ ] Review worker processing times
- [ ] Check Redis memory usage
- [ ] Monitor Railway resource usage (CPU, memory)
- [ ] Review cost dashboard

**Monthly:**
- [ ] Optimize worker count based on traffic patterns
- [ ] Review and optimize database queries
- [ ] Update dependencies (`pip list --outdated`)

#### Key Metrics to Track

1. **Queue Depth:** How many jobs waiting
   - Check Redis: `LLEN crew_jobs` command
   - Goal: Keep under 10-20 for good latency

2. **Worker Utilization:** Are workers busy or idle?
   - Check Celery logs for task start/complete messages
   - Scale up if workers constantly busy
   - Scale down if workers mostly idle

3. **Job Duration:** How long jobs take
   - Add logging in `backend/tasks.py`
   - Track P50, P95, P99 durations
   - Optimize slow jobs

4. **Error Rate:** Failed jobs
   - Monitor Railway logs for exceptions
   - Check job status distribution in database
   - Investigate and fix failed job patterns

### 10.5 Scaling Strategy

#### When to Scale UP (More Resources per Instance)

**Symptoms:**
- High CPU usage (>80% sustained)
- High memory usage (>80%)
- API response times increasing
- Worker tasks timing out

**Actions:**
1. Go to Railway Settings → Resources
2. Increase CPU/Memory allocation
3. Monitor performance improvement

#### When to Scale OUT (More Instances)

**Symptoms:**
- Queue depth consistently high (>20 jobs)
- API response time high despite low CPU
- Workers can't keep up with job submissions

**Actions:**

**Scale Workers:**
1. Go to Railway service settings
2. Increase replica count for worker process
3. Start with +1 worker, monitor queue depth
4. Continue scaling until queue depth is healthy

**Scale API:**
1. Less common to need multiple API instances initially
2. Scale when API CPU/memory is high
3. Ensure Redis-backed rate limiting is active
4. Railway will load balance across API instances

#### Cost-Effective Scaling Tips

1. **Scale workers first** - Usually the bottleneck
2. **Use autoscaling** (Pro plan) - Only pay for what you need
3. **Monitor queue depth** - Scale based on data, not guesses
4. **Optimize job duration** - Faster jobs = need fewer workers
5. **Use caching** - Reduce redundant work
6. **Schedule heavy tasks** - Run during off-peak hours if possible

### 10.6 Deployment Checklist

Before going live with production traffic:

**Pre-Deployment:**
- [ ] All tests pass locally (`python scripts/test.py --all`)
- [ ] Redis Cloud database created and accessible
- [ ] All environment variables documented
- [ ] Frontend updated with Railway API URL
- [ ] CORS settings updated in `backend/main.py` (if needed)

**Deployment:**
- [ ] Railway project created from GitHub
- [ ] All environment variables set in Railway
- [ ] Both `web` and `worker` processes running
- [ ] Health check endpoint returns 200 OK
- [ ] Test job submission and completion works
- [ ] Redis connection successful (check logs)

**Post-Deployment:**
- [ ] Monitor logs for 1 hour for any errors
- [ ] Submit real test job and verify completion
- [ ] Check worker is processing jobs correctly
- [ ] Verify rate limiting works across requests
- [ ] Set up alerts for critical errors
- [ ] Document Railway dashboard access for team

**Ongoing:**
- [ ] Weekly: Review error logs and performance metrics
- [ ] Monthly: Check Railway costs and optimize
- [ ] As needed: Scale workers based on queue depth
- [ ] As needed: Update dependencies and redeploy

---

## Next Steps After Deployment

Once deployed and stable:

1. **Gather user feedback** (surveys, analytics, support tickets)
3. **Optimize performance** based on real usage data
4. **Scale infrastructure** as user base grows
5. **Consider monetization** if costs increase significantly

---

## Support & Resources

**Documentation:**
- [Railway Docs](https://docs.railway.app)
- [Supabase Docs](https://supabase.com/docs)
- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages)
- [FastAPI Deployment Docs](https://fastapi.tiangolo.com/deployment/)

**Monitoring Tools:**
- [Railway Dashboard](https://railway.app) - Backend monitoring
- [Supabase Dashboard](https://supabase.com/dashboard) - Database monitoring

**Community:**
- Railway Discord: https://discord.gg/railway
- Supabase Discord: https://discord.supabase.com
- CrewAI Discord: https://discord.com/invite/X4JWnZnxPb

---

## Appendix: Deployment Commands Reference

### Railway CLI Commands

```bash
# Install Railway CLI
npm install -g @railway/cli
# OR
brew install railway  # macOS
# OR
curl -fsSL https://railway.app/install.sh | sh  # Linux/macOS

# Login
railway login

# Link to project
cd /path/to/scholar_source
railway link

# Check current status
railway status  # Shows current environment and service

# Switch environments
railway environment production
railway environment development

# View logs
railway logs  # All services
railway logs --filter worker  # Worker only
railway logs --follow  # Follow in real-time

# View variables
railway variables  # All variables for current environment
railway variables | grep REDIS_URL  # Specific variable

# Set environment variable
railway variables set OPENAI_API_KEY=sk-proj-...

# Run command in Railway environment
railway run python scripts/test.py --redis

# Deploy manually (auto-deploy via GitHub is recommended)
railway up

# Open dashboard
railway open
```

### Railway Quick Reference

**Check Current Environment:**
- Railway Dashboard: Look at top-left breadcrumb `[Project] > [Environment] > [Service]`
- Railway CLI: `railway status`
- In logs: Look for `RAILWAY_ENVIRONMENT_NAME` variable

**Environment Variables Railway Sets:**
- `RAILWAY_ENVIRONMENT_NAME` - Environment name (production, development)
- `RAILWAY_GIT_BRANCH` - Git branch (main, develop)
- `RAILWAY_GIT_COMMIT_SHA` - Full commit hash
- `RAILWAY_SERVICE_NAME` - Service name (web, worker)
- `RAILWAY_PROJECT_NAME` - Project name

**Typical Setup:**
- Production: `main` branch → `production` environment
- Development: `develop` branch → `development` environment
- Each environment has separate variables, databases, Redis instances

### Cloudflare Pages Deployment

```bash
# Install Wrangler CLI (optional)
npm install -g wrangler

# Login
wrangler login

# Deploy manually (auto-deploy via GitHub is recommended)
cd web && npm run build
wrangler pages deploy dist --project-name=scholar-source

# View deployment logs
wrangler pages deployment list
```

### Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref your-project-ref

# Run migrations (for future schema updates)
supabase db push

# Backup database
supabase db dump -f backup.sql
```

---

**Deployment Plan Version:** 1.1
**Last Updated:** December 2024
**Status:** Ready for production deployment with scaling support
