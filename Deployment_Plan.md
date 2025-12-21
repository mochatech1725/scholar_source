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

- [ ] Git repository with all code committed
- [ ] OpenAI API key with Tier 2+ rate limits (450k TPM)
- [ ] Serper API key for web search
- [ ] Supabase account created
- [ ] Railway account created (free to sign up)
- [ ] Cloudflare account created (free to sign up)
- [ ] Domain name (optional, but recommended for production)

---

## Part 1: Database Setup (Supabase)

### 1.1 Create Supabase Project

1. Go to https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in project details:
   - **Name**: `scholar-source-prod`
   - **Database Password**: Generate strong password (save in password manager!)
   - **Region**: Choose closest to your users (e.g., US East, EU West)
4. Click **"Create new project"** (takes ~2 minutes)

### 1.2 Create Database Schema

1. In Supabase Dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Paste the following SQL:

```sql
-- Jobs table to store job status and results
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    inputs JSONB NOT NULL,
    results JSONB,
    raw_output TEXT,
    error TEXT,
    status_message TEXT,
    search_title TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for faster lookups
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (public access for MVP)
-- TODO: Restrict this in Phase 2 when adding user authentication
CREATE POLICY "Enable all access for jobs" ON jobs
    FOR ALL USING (true);
```

4. Click **"Run"** to execute

### 1.3 Get Supabase Credentials

1. In Supabase Dashboard, go to **Project Settings** → **API**
2. Copy and save these values:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon/public key** (long string starting with `eyJ...`)

### 1.4 Enable Realtime (Optional)

If you plan to use WebSockets for real-time updates in Phase 2:

1. Go to **Database** → **Replication**
2. Enable replication for `jobs` table
3. Go to **Project Settings** → **API** → **Realtime**
4. Enable Realtime for `public.jobs`

**Status:** ✅ Database configured and ready

---

## Part 2: Backend Deployment (Railway)

### 2.1 Prepare Backend for Deployment

1. **Create `railway.json` configuration file:**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. **Create `Procfile` (alternative):**

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

3. **Update `pyproject.toml` to ensure all dependencies are listed:**

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

4. **Update CORS origins in `backend/main.py`:**

```python
# Update to include your production frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://your-app.pages.dev",  # Cloudflare Pages (temp URL)
        "https://yourdomain.com",  # Your custom domain (if applicable)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

5. **Commit all changes:**

```bash
git add .
git commit -m "Prepare backend for Railway deployment"
git push origin main
```

### 2.2 Deploy to Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub account
5. Select your `scholar_source` repository
6. Railway will auto-detect Python and start building

### 2.3 Configure Environment Variables

1. In Railway dashboard, click on your deployed service
2. Go to **"Variables"** tab
3. Add the following environment variables:

```bash
OPENAI_API_KEY=sk-proj-...your_key_here
SERPER_API_KEY=...your_serper_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGc...your_anon_key_here
```

4. Click **"Deploy"** to restart with new variables

### 2.4 Configure Railway Service

1. **Set up custom domain (optional):**
   - Go to **"Settings"** → **"Domains"**
   - Add custom domain (e.g., `api.yourdomain.com`)
   - Update your DNS records as instructed

2. **Configure health checks:**
   - Go to **"Settings"** → **"Health Checks"**
   - Set health check path: `/api/health`
   - Set timeout: 30 seconds

3. **Enable always-on service:**
   - Go to **"Settings"** → **"Service"**
   - Ensure service is on **"Always On"** plan ($5/month)
   - This prevents cold starts and ensures 24/7 availability

4. **Configure resource limits (optional):**
   - Go to **"Settings"** → **"Resources"**
   - Set memory limit: 512MB-1GB (should be sufficient)
   - Set CPU limit: 1-2 vCPUs

### 2.5 Verify Backend Deployment

1. Copy your Railway deployment URL (e.g., `https://your-app.up.railway.app`)
2. Test the health endpoint:

```bash
curl https://your-app.up.railway.app/api/health
```

**Expected response:**
```json
{"status": "healthy"}
```

3. Test job submission (optional):

```bash
curl -X POST https://your-app.up.railway.app/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "university_name": "MIT",
    "course_name": "Introduction to Algorithms",
    "book_title": "Introduction to Algorithms",
    "book_author": "Cormen, Leiserson, Rivest, Stein"
  }'
```

**Status:** ✅ Backend deployed and running on Railway

---

## Part 3: Frontend Deployment (Cloudflare Pages)

### 3.1 Prepare Frontend for Deployment

1. **Update `web/.env.production` (create if doesn't exist):**

```bash
VITE_API_URL=https://your-app.up.railway.app
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

4. **Commit changes:**

```bash
git add .
git commit -m "Prepare frontend for Cloudflare Pages deployment"
git push origin main
```

### 3.2 Deploy to Cloudflare Pages

1. Go to https://dash.cloudflare.com
2. Navigate to **"Workers & Pages"**
3. Click **"Create application"** → **"Pages"** → **"Connect to Git"**
4. Authorize Cloudflare to access your GitHub account
5. Select your `scholar_source` repository

### 3.3 Configure Build Settings

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

### 3.4 Add Environment Variables

1. Click **"Environment variables"**
2. Add the following:

```bash
VITE_API_URL=https://your-app.up.railway.app
```

3. Select **"Production"** environment
4. Click **"Save"**

### 3.5 Deploy

1. Click **"Save and Deploy"**
2. Wait for build to complete (~2-5 minutes)
3. Cloudflare will provide a temporary URL: `https://your-app.pages.dev`

### 3.6 Configure Custom Domain (Optional)

1. Go to **"Custom domains"** tab
2. Click **"Set up a custom domain"**
3. Enter your domain (e.g., `app.yourdomain.com` or `yourdomain.com`)
4. Follow DNS configuration instructions
5. Wait for SSL certificate to provision (~5-10 minutes)

### 3.7 Verify Frontend Deployment

1. Visit your Cloudflare Pages URL: `https://your-app.pages.dev`
2. Test the form submission workflow:
   - Fill in course information
   - Submit the form
   - Wait for job to complete
   - Verify results display correctly
3. Test shareable link feature
4. Test copy and export buttons

**Status:** ✅ Frontend deployed and accessible via Cloudflare Pages

---

## Part 4: Post-Deployment Configuration

### 4.1 Update Backend CORS

Now that you have the production frontend URL, update the backend CORS configuration:

1. Edit `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://your-app.pages.dev",  # Cloudflare Pages
        "https://yourdomain.com",  # Custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. Commit and push:

```bash
git add backend/main.py
git commit -m "Update CORS for production frontend URLs"
git push origin main
```

3. Railway will auto-deploy the update (~1-2 minutes)

### 4.2 Set Up Monitoring

#### Railway (Backend Monitoring)

1. Go to Railway dashboard → **"Observability"**
2. Enable metrics collection
3. Set up alerts for:
   - High error rates (>5% of requests)
   - High memory usage (>80%)
   - Service downtime

#### Supabase (Database Monitoring)

1. Go to Supabase dashboard → **"Reports"**
2. Monitor:
   - Database size (stay under 500MB for free tier)
   - API requests (stay under limits)
   - Active connections

#### Cloudflare (Frontend Monitoring)

1. Go to Cloudflare dashboard → **"Analytics"**
2. Monitor:
   - Page views
   - Bandwidth usage (unlimited on free tier)
   - Error rates

### 4.3 Set Up Error Tracking (Optional)

Consider adding error tracking services:

**Option 1: Sentry (Recommended)**

```bash
# Backend
pip install sentry-sdk

# Frontend
npm install @sentry/react
```

**Option 2: LogRocket**

```bash
npm install logrocket
```

**Option 3: Rollbar**

```bash
pip install rollbar
npm install rollbar
```

### 4.4 Configure Backups

#### Supabase Database Backups

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

1. **Submit a job:**
   - Go to your production URL
   - Fill in course information
   - Submit the form
   - Note the job ID

2. **Monitor job execution:**
   - Watch the loading status updates
   - Verify status polling works (every 2 seconds)
   - Wait for job completion (2-5 minutes)

3. **Verify results:**
   - Check that results display correctly
   - Test "Copy" buttons
   - Test "Share Results" button
   - Test shareable link by opening in incognito window

4. **Test error handling:**
   - Submit form with no inputs → should show validation error
   - Visit invalid job ID → should show 404
   - Turn off Railway service → frontend should handle gracefully

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
   - Reload shareable link → results should persist

### 5.3 Security Testing

1. **Test CORS:**
   - Try accessing API from unauthorized origin → should be blocked
   - Verify only allowed origins can make requests

2. **Test SQL injection:**
   - Try malicious inputs in form fields
   - Verify Supabase safely handles all inputs (JSONB fields are safe)

3. **Test rate limiting (if implemented):**
   - Submit many requests quickly
   - Verify rate limiting works

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

### 8.3 Database Rollback

**Restore from backup:**
1. Go to Supabase dashboard → **"Database"** → **"Backups"**
2. Select backup to restore
3. Click **"Restore"**
4. **Warning:** This will overwrite current database!

---

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
- Archive old results to cold storage (S3)
- Optimize JSONB fields to reduce size

**Monitor and alert:**
- Set up billing alerts in OpenAI (e.g., alert at $50)
- Monitor Railway usage (alert if approaching next tier)
- Track Supabase database size (alert at 450MB)

---

## Part 10: Troubleshooting Common Issues

### Issue 1: Backend Won't Start on Railway

**Symptoms:** Deployment fails, service crashes immediately

**Diagnosis:**
```bash
# Check Railway logs
# Go to Railway dashboard → Deployments → View Logs
```

**Solutions:**
- Missing environment variables → Add in Railway dashboard
- Python version mismatch → Update `pyproject.toml`
- Missing dependencies → Update `pyproject.toml` dependencies
- Port binding issue → Ensure using `$PORT` environment variable

### Issue 2: Frontend Can't Connect to Backend

**Symptoms:** Form submission fails, CORS errors in browser console

**Diagnosis:**
```javascript
// Check browser console for errors
// Look for CORS error messages
```

**Solutions:**
- CORS not configured → Add frontend URL to `allow_origins` in `backend/main.py`
- Wrong API URL → Check `VITE_API_URL` in Cloudflare Pages environment variables
- Backend down → Check Railway dashboard for backend status

### Issue 3: Jobs Never Complete

**Symptoms:** Loading status stuck on "running", no results

**Diagnosis:**
- Check Railway logs for backend errors
- Check Supabase database for job status

**Solutions:**
- OpenAI rate limit → Wait for reset or upgrade tier
- Crew execution error → Check Railway logs for Python traceback
- Database connection issue → Verify Supabase credentials

### Issue 4: High OpenAI Costs

**Symptoms:** Unexpected high bills from OpenAI

**Diagnosis:**
- Check OpenAI dashboard → Usage → Token usage
- Look for spike in GPT-4o usage

**Solutions:**
- Downgrade more agents to GPT-4o-mini
- Implement request throttling
- Add monthly spending cap in OpenAI dashboard
- Review and optimize agent prompts

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

- [ ] CORS restricted to known origins only
- [ ] Rate limiting implemented (add in Phase 2)
- [ ] Input validation on all endpoints
- [ ] HTTPS enforced (automatic with Railway/Cloudflare)

### 11.4 Frontend Security

- [ ] Content Security Policy (CSP) headers configured
- [ ] No sensitive data in localStorage
- [ ] XSS prevention (React handles this ✅)
- [ ] No API keys in frontend code

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
- **Shareable links clicked**: Measure viral growth
- **User retention**: % of users who return within 7 days

### Cost Metrics

- **Cost per job**: Total monthly costs ÷ jobs submitted
- **OpenAI cost per job**: OpenAI costs ÷ jobs submitted
- **Infrastructure cost per user**: Fixed costs ÷ monthly active users

---

## Next Steps After Deployment

Once deployed and stable:

1. **Gather user feedback** (surveys, analytics, support tickets)
2. **Plan Phase 2 features** (see [Future_plans.md](Future_plans.md))
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
- [UptimeRobot](https://uptimerobot.com) - Free uptime monitoring
- [Sentry](https://sentry.io) - Error tracking
- [Railway Dashboard](https://railway.app) - Backend monitoring
- [Supabase Dashboard](https://supabase.com/dashboard) - Database monitoring

**Community:**
- Railway Discord: https://discord.gg/railway
- Supabase Discord: https://discord.supabase.com
- CrewAI Discord: https://discord.com/invite/X4JWnZnxPb

---

## Appendix: Deployment Commands Reference

### Railway Deployment

```bash
# Install Railway CLI (optional)
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy manually (auto-deploy via GitHub is recommended)
railway up

# View logs
railway logs

# Set environment variable
railway variables set OPENAI_API_KEY=sk-proj-...
```

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

**Deployment Plan Version:** 1.0
**Last Updated:** December 2024
**Status:** Ready for production deployment
