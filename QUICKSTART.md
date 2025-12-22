# QuickStart Guide

Get ScholarSource up and running in 5 minutes!

## Prerequisites

- ✅ Python 3.10+ with virtual environment activated
- ✅ Node.js and npm installed
- ✅ Supabase project created with jobs table
- ✅ Environment variables configured in `.env`

## Step 1: Install Dependencies

### Backend
```bash
# From project root
pip install -e .
```

### Frontend
```bash
# Already installed during setup
cd web
# If needed: npm install
```

## Step 2: Start Services

Open **two terminal windows**:

### Terminal 1: Backend
```bash
cd /Users/teial/Tutorials/AI/scholar_source
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: **http://localhost:8000**

### Terminal 2: Frontend
```bash
cd /Users/teial/Tutorials/AI/scholar_source/web
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

## Step 3: Test It!

1. Open http://localhost:5173 in your browser
2. Fill in "Course Name" field (e.g., "Introduction to Algorithms")
3. Click "Find Resources"
4. Wait 1-5 minutes for results
5. Copy URLs and share!

## Verify It's Working

### Check Backend Health
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

### Check Frontend
Open http://localhost:5173 - should see the form

## Troubleshooting

### Backend won't start
- Check `.env` has SUPABASE_URL and SUPABASE_ANON_KEY
- Verify virtual environment is activated
- Run `pip install -e .` again

### Frontend won't start
- Run `cd web && npm install`
- Check port 5173 isn't in use

### Database errors
- Verify Supabase project is running
- Check you ran the SQL schema in Supabase SQL Editor
- Verify API keys are correct

### CORS errors
- Ensure backend is running on port 8000
- Check CORS origins in backend/main.py include "http://localhost:5173"

## Next Steps

- Read [BACKEND_TESTING.md](BACKEND_TESTING.md) for API testing
- Read [FRONTEND_TESTING.md](FRONTEND_TESTING.md) for UI testing
- Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for full overview

## Development Workflow

1. Start backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. Start frontend: `cd web && npm run dev`
3. Make changes to code
4. Both servers auto-reload on file changes
5. Test in browser

## Production Deployment

When ready for production, see [Deployment_Plan.md](Deployment_Plan.md)

---

**🎉 You're ready to go!**
