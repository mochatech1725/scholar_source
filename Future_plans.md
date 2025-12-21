# ScholarSource Implementation Roadmap

This document tracks the implementation plan for the ScholarSource web application.

---

## Phase 1: MVP Web Application (Current Implementation)

Full-stack web application with React/Vite frontend and FastAPI backend that integrates with the existing ScholarSource CrewAI implementation. The API handles long-running crew executions asynchronously with job status polling, and parses markdown output into structured JSON for display in a table.

### User Decisions
- **Frontend:** React + Vite (modern framework)
- **Async Strategy:** Background jobs with status polling
- **Output Format:** Parse markdown into structured table data
- **Storage:** Supabase (PostgreSQL) - Production-ready persistence
- **MVP Feature:** Save/share result links included

### Project Structure (After Implementation)

```
/Users/teial/Tutorials/AI/scholar_source/
├── backend/                      # NEW - FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── models.py                 # Pydantic models for requests/responses
│   ├── database.py               # Supabase client and DB operations
│   ├── jobs.py                   # Background job management (uses Supabase)
│   ├── crew_runner.py            # Wrapper for ScholarSource crew
│   └── markdown_parser.py        # Parse crew output to structured JSON
│
├── web/                          # NEW - React/Vite frontend
│   ├── public/                   # Static assets
│   ├── src/
│   │   ├── App.jsx               # Main app component
│   │   ├── main.jsx              # Entry point
│   │   ├── components/
│   │   │   ├── CourseForm.jsx    # Form component
│   │   │   ├── ResultsTable.jsx  # Results display
│   │   │   └── LoadingStatus.jsx # Job status polling UI
│   │   ├── api/
│   │   │   └── client.js         # API client functions
│   │   └── styles/
│   │       └── App.css           # Styles (from mockup)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.local                # API URL configuration
│
├── src/scholar_source/           # EXISTING - CrewAI implementation
│   ├── crew.py                   # No changes needed
│   ├── main.py                   # CLI still works independently
│   └── config/                   # No changes needed
│
├── pyproject.toml                # UPDATE - Add FastAPI dependencies
└── README.md                     # UPDATE - Add web app documentation
```

### Implementation Tasks

#### Part 0: Supabase Setup
- [ ] Create Supabase project
- [ ] Create jobs table in database
- [ ] Set up Row Level Security policies
- [ ] Get API credentials (URL and anon key)
- [ ] Add credentials to .env file

#### Part 1: Backend (FastAPI) Implementation
- [ ] Update pyproject.toml with FastAPI dependencies
- [ ] Create backend directory structure
- [ ] Implement backend/database.py (Supabase client)
- [ ] Implement backend/models.py (Pydantic models)
- [ ] Implement backend/jobs.py (job management with Supabase)
- [ ] Implement backend/crew_runner.py (CrewAI integration)
- [ ] Implement backend/markdown_parser.py (parse markdown to JSON)
- [ ] Implement backend/main.py (FastAPI app with 4 endpoints)
- [ ] Test backend API locally

#### Part 2: Frontend (React/Vite) Implementation
- [ ] Initialize React/Vite project
- [ ] Install react-router-dom dependency
- [ ] Implement web/src/api/client.js (API client)
- [ ] Implement web/src/components/CourseForm.jsx
- [ ] Implement web/src/components/LoadingStatus.jsx
- [ ] Implement web/src/components/ResultsTable.jsx
- [ ] Implement web/src/pages/HomePage.jsx
- [ ] Implement web/src/pages/ResultsPage.jsx (shareable results)
- [ ] Implement web/src/App.jsx (routing)
- [ ] Port CSS from mockup to web/src/styles/App.css
- [ ] Create web/.env.local configuration
- [ ] Create web/vite.config.js
- [ ] Test frontend locally

#### Part 3: Integration & Testing
- [ ] Test full workflow (form submission → job polling → results display)
- [ ] Test shareable results links
- [ ] Test error handling (network errors, invalid inputs, etc.)
- [ ] Test persistence (jobs survive server restarts)
- [ ] Validate CORS configuration
- [ ] Test copy and export buttons

#### Part 4: Documentation
- [ ] Update README.md with web app setup instructions
- [ ] Create backend/README.md (API documentation)
- [ ] Create web/README.md (frontend documentation)

#### Part 5: Deployment
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Cloudflare Pages
- [ ] Configure production environment variables
- [ ] Test production deployment
- [ ] Verify shareable links work in production

### Success Criteria
- [ ] Supabase database configured with jobs table
- [ ] Jobs persisted to Supabase (survive restarts)
- [ ] Backend API running on port 8000
- [ ] Frontend dev server running on port 5173
- [ ] Form accepts course inputs and validates at least one field
- [ ] API creates background job and returns job_id
- [ ] Frontend polls job status every 2 seconds
- [ ] Crew executes and generates resources
- [ ] Markdown parsed into structured JSON
- [ ] Results displayed in table matching mockup design
- [ ] Copy buttons functional
- [ ] Share Results button copies shareable URL
- [ ] Shareable link `/results/{job_id}` works
- [ ] Results page loads from shared link
- [ ] Shared links persist after server restart
- [ ] Export to NotebookLM button functional
- [ ] Error states handled gracefully

---

## Phase 2: Future Enhancements

Post-MVP features to enhance functionality, scalability, and user experience.


### Real-time Features
- [ ] WebSocket support for real-time progress updates
- [ ] Live progress streaming instead of polling
- [ ] Real-time notifications when job completes

### Advanced Features

- [ ] Direct NotebookLM API integration (auto-import resources)

### Sharing & Collaboration
- [ ] Share results via email

### Resource Management
- [ ] Job deletion/cleanup (automatic or manual)
- [ ] Job expiration policies (auto-delete after 30/60/90 days)


### AI & Intelligence
- [ ] Model fine-tuning for better resource discovery
- [ ] A/B testing for agent prompts

### Communication
- [ ] Email notifications when job completes


### Content & Resources
- [ ] OCR for scanned PDFs
- [ ] Support for non-English textbooks
- [ ] Automatic textbook ISBN detection from images

### Security & Compliance
- [ ] Enhanced Row Level Security (RLS) policies
- [ ] Content Security Policy (CSP)
- [ ] Penetration testing

---

## Technical Debt & Improvements

Ongoing improvements to code quality, maintainability, and developer experience.

- [ ] Refactor markdown parser for better accuracy
- [ ] Add TypeScript to frontend
- [ ] Add type hints to all Python code
- [ ] Improve error messages and user feedback
- [ ] Add logging throughout backend
- [ ] Create comprehensive test suite
- [ ] Document API with OpenAPI/Swagger
- [ ] Add code comments and docstrings
- [ ] Set up pre-commit hooks (linting, formatting)
- [ ] Standardize code formatting (Black, Prettier)

---

## Notes

- Phase 1 is the current focus and must be completed before Phase 2
- Phase 2 items are unordered and can be prioritized based on user feedback
- Check off items with `[x]` as they are completed
- Add new items as needed with a new checkbox `[ ]`
