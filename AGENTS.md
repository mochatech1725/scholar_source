# Codex Development Guidelines

## React Best practices

Use this as a checklist / rubric that Codex should adhere to when generating or refactoring React code.

---

## Core React patterns

- Prefer **functional** components and Hooks; treat class components as legacy unless integrating with old code.
- Keep components small, focused, and single‑responsibility; if a component grows beyond ~150–200 lines or handles several concerns, split it.
- Co-locate logic with the component that owns it (state, derived data, effects, queries) instead of scattering utilities and hooks across the app.
- Use composition over inheritance: accept children/slots instead of deeply nested prop options or config objects.
- Use controlled components for form elements whenever you need validation, instant feedback, or complex interactions; otherwise consider uncontrolled refs for simple cases.

***

## State and data fetching

- Keep state as **local** as possible; lift state only when multiple components truly share it.
- Avoid prop drilling across many levels; use Context for cross-cutting concerns and consider a lightweight state library (Zustand, Jotai, Redux Toolkit) for complex global state.
- Store the minimal state needed; derive everything else from props or existing state instead of duplicating values.
- Treat server as the source of truth for server data and client state as a cache or view model.
- Use a dedicated data-fetching library (TanStack Query / React Query or SWR) instead of ad‑hoc useEffect + fetch for anything beyond trivial requests.
- Normalize async flows: handle loading, error, empty, and success states explicitly and consistently.

***

## React 18 features and concurrency

- Use Suspense for data fetching and code-splitting boundaries to improve perceived loading and structure async flows.
- Use concurrent APIs like useTransition and useDeferredValue to keep the UI responsive during expensive updates or filtering.
- Design UI so that non‑critical parts can be deferred or streamed rather than blocking the initial render.

***

## React Server Components (RSC) and server/client split

(For Next.js App Router or other RSC-enabled setups.)

- Default to Server Components for data fetching, heavy computation, and non‑interactive UI to reduce client bundle size.
- Keep Server Components stateless and side‑effect free; do not use client-only hooks (useState, useEffect, browser APIs) in them.
- Use Client Components only when interactivity or browser APIs are required, and keep them as small and focused as possible.
- Pay attention to boundaries: pass data from Server to Client via props, avoid leaking client concerns into server code.
- Be cautious with third‑party libraries in Server Components; only use libraries that are safe on the server (no window/document/localStorage).

***

## Performance and rendering

- Minimize unnecessary re-renders:
  - Use React.memo for pure presentational components with stable props.
  - Use useCallback and useMemo for expensive computations or when prop identity matters (e.g., passed to memoized children).
- Avoid inline anonymous functions and object/array literals in hot rendering paths when they cause prop identity churn.
- Use stable, unique keys for list items; never use array index as key when list can be reordered or filtered.[
- Virtualize large lists and tables to avoid rendering hundreds/thousands of DOM nodes.
- Avoid overusing Context; large or frequently changing contexts can trigger expensive tree-wide re-renders—consider splitting context or using selectors/state libraries.
- Split bundles using dynamic import and React.lazy for heavy, rarely used routes or components.
- Regularly profile the app (React DevTools Profiler, Web Vitals, browser performance tools) and optimize based on real bottlenecks, not guesses.

***

## Structure, organization, and reuse

- Organize files by feature/module instead of strictly by type; keep components, hooks, and tests for a feature together.
- Extract reusable UI patterns as shared components and shared hooks (e.g., useForm, useModal, useFetch) to avoid duplication.
- Keep hooks pure: avoid doing non‑React side effects directly in custom hooks unless the hook is specifically about that effect, and document clearly when they occur.
- Prefer simple, predictable naming: useFoo for hooks, PascalCase for components, clear prop names instead of abbreviations.
- Co-locate tests, styles, and stories with their components to improve discoverability and refactoring.

***

## TypeScript and safety

- Use TypeScript (or at least JSDoc types) for components, hooks, and utilities to catch errors at compile time and improve IDE help.
- Prefer typed props and state over any/unknown; model domain concepts with discriminated unions instead of booleans when multiple states are possible.
- Type external data at the boundary (e.g., API responses), and consider runtime validation for untrusted inputs.

***

## JSX, styling, and DOM

- Keep JSX clean and readable; avoid deeply nested markup by extracting subcomponents.
- Avoid putting complex logic directly in JSX; move it into variables or helper functions above the return.
- Use semantic HTML tags and ARIA attributes; avoid div‑soup, especially for interactive elements.
- Prefer CSS modules, utility CSS (like Tailwind), or well‑structured CSS‑in‑JS with attention to performance; avoid global styles that leak across features.
- Use modern image optimizations (lazy loading, responsive images, modern formats, or framework-level image components) for performance.

***

## Side effects and lifecycle

- Use useEffect only for real side effects (subscriptions, event listeners, imperative APIs, syncing with non‑React systems), not for synchronous derivations that can be computed during render.
- Carefully manage effect dependencies; prefer making effects idempotent and narrowing their scope instead of disabling lint rules.
- Clean up subscriptions, timers, event listeners, and observers in the effect cleanup function to prevent leaks.
- Avoid "fetch in every effect" anti‑pattern; centralize data fetching via libraries or well-designed hooks.

***

## Error handling, boundaries, and UX

- Use Error Boundaries around major app sections (routes, dashboards, complex widgets) to avoid full app crashes.
- Provide meaningful fallbacks for loading and error states (skeletons/spinners + retry, not just blank or generic messages).
- Design for progressive enhancement: render useful content early and progressively hydrate/upgrade with client interactivity.

***

## Testing and maintainability

- Write tests for critical flows (auth, payments, core workflows) using Jest/Vitest for unit tests and React Testing Library for behavior-focused component tests.
- Use Cypress/Playwright (or similar) for end‑to‑end tests on key user journeys.
- Favor testing behavior and user-visible outcomes rather than implementation details or specific hook calls.
- Keep strict ESLint + Prettier (or equivalent) configs and ensure code always passes lint/format checks.

***

## When instructing Codex (or another generator)

Provide instructions such as:

- "Use functional components and Hooks only; no class components."
- "Keep components small and focused, and extract reusable pieces into separate components or hooks."
- "Use React Query (or SWR) for data fetching, with clear handling of loading and error states."
- "Optimize for performance: avoid unnecessary re-renders, use memoization wisely, use stable keys, and consider list virtualization."
- "In RSC frameworks, default to Server Components for data fetching and keep Client Components minimal and interactive."
- "Use TypeScript with strict, explicit types and keep JSX, effects, and state management clean, predictable, and well-tested."

---

## Tailwind and CSS Best Practices

Use this as a checklist / rubric that Codex should adhere to when generating or refactoring Tailwind CSS and React code.

### 1. Project & Tailwind config

- Keep all Tailwind setup in `tailwind.config.(js|ts)` and a single main CSS entry (e.g. `src/index.css` or `src/global.css`).
- Use the `content` option correctly so unused classes get purged.
- Extend Tailwind instead of replacing it:
  - Add design tokens (colors, spacing, fonts, radii, breakpoints) under `theme.extend` to encode your design system.
  - Prefer semantic tokens: e.g. `brand`, `accent`, `danger`, not raw hex names.
- Enable/keep JIT (default in modern Tailwind) for on-demand class generation.
- Use official plugins where useful (forms, typography, line-clamp, etc.).

**Example:**
```js
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f766e",
          soft: "#ccfbf1",
        },
      },
      spacing: {
        128: "32rem",
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
```

### 2. Utility-first mindset

- Prefer Tailwind utility classes co-located in JSX instead of separate CSS.
- Start by styling at the component/page level, then extract into smaller components when patterns repeat. Avoid premature abstraction.
- Let Tailwind's scales drive design (spacing, font sizes, colors) rather than arbitrary values; this keeps the UI consistent.
- Use Tailwind's mobile-first responsive prefixes: `sm: md: lg: xl: 2xl:`.
  - Example: `p-3 md:p-4 lg:p-6` for progressively larger padding.

### 3. ClassName organization in React

- Keep className strings readable:
  - Group related utilities: layout → spacing → typography → decoration → state.
  - Put variants (hover:, focus:, sm:, dark:) next to the base class they modify.
- For complex components, compose class names instead of giant literals:
  - Use helpers like `clsx` or `classnames`.
  - Use `tailwind-merge` (or `twMerge`) to resolve conflicting utilities.
- Avoid passing raw Tailwind className fragments as many small props; prefer higher-level props like `variant`, `size`, `intent`, then map them to className internally.

**Example:**
```tsx
const base =
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";

const variants: Record<"primary" | "secondary", string> = {
  primary: "bg-brand text-white hover:bg-emerald-700",
  secondary: "bg-white text-gray-900 border border-gray-300 hover:bg-gray-50",
};

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      className={twMerge(base, variants[variant], className)}
      {...props}
    />
  );
}
```

### 4. When (not) to use @apply or extra CSS

- Prefer pure utilities first; only introduce custom CSS when:
  - You repeat long utility chains across many components.
  - You need true pseudo-elements or complex selectors.
- Use `@layer components` and `@apply` for shared component styles, but don't rebuild a BEM-style system—keep things minimal.
- Avoid heavy use of `@apply` for variants like `hover:`/`focus:` if it hides what the component actually does.

**Example (moderate use of @apply in a components layer):**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn-primary {
    @apply inline-flex items-center justify-center rounded-md bg-brand text-white
      px-4 py-2 text-sm font-medium shadow-sm hover:bg-emerald-700
      focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2;
  }
}
```

### 5. Component patterns with React + Tailwind

- Use composition + variants:
  - Simple primitive components (Button, Card, Input, Tag).
  - Map `variant`, `size`, and `state` props to Tailwind class maps.
- Keep components small and focused; if JSX becomes too noisy, split into subcomponents instead of introducing global CSS.
- For reusable layout primitives (Stack, Container, Grid), bake in sensible defaults (padding, max-width, gap) with Tailwind classes.
- Treat Tailwind config + primitives as a lightweight design system.

### 6. Responsive & state variants

- Follow a consistent order in className:
  - Base → responsive → state (hover, focus, active) → dark mode.
- Use Tailwind's responsive modifiers instead of custom media queries in CSS whenever possible.
- Use dark mode and prefers-reduced-motion via Tailwind's built-in variants if your app supports them.

**Example:**
```tsx
<div className="
  flex flex-col gap-3
  sm:flex-row sm:items-center
  p-4 sm:p-6
  bg-white dark:bg-gray-900
  hover:bg-gray-50 dark:hover:bg-gray-800
">
  ...
</div>
```

### 7. Accessibility & semantics

- Tailwind doesn't replace semantic HTML:
  - Use proper elements: `<button>`, `<a>`, `<label>`, `<nav>`, `<main>`, etc.
- Use focus styles, not `outline:none` without replacement.
  - Tailwind provides `focus:*` utilities, `focus-visible:*`, and ring utilities.
- Ensure color contrast meets WCAG; rely on your design tokens across the app, not ad hoc colors.
- Use ARIA attributes and semantic roles where needed, same as with normal CSS.

**Example:**
```tsx
<button
  type="button"
  aria-label="Close dialog"
  className="
    inline-flex items-center justify-center rounded-full
    bg-gray-100 hover:bg-gray-200
    text-gray-700
    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand
  "
>
  ×
</button>
```

### 8. Performance & bundle size

- Ensure purge/content configuration covers all JSX/TSX files so unused classes are removed in production.
- Avoid constructing class names dynamically with string concatenation that PurgeCSS cannot detect; use explicit class literals or known variant maps instead.
- Prefer Tailwind utilities over huge custom CSS blocks; this keeps your final CSS small and tree-shake-friendly.
- Keep global CSS minimal (resets, typography, a few component-level @apply rules) so Tailwind can do most of the heavy lifting.

### 9. Folder structure & organization

- Example structure for React + Tailwind:
  ```
  src/
    components/
      ui/
        Button.tsx
        Input.tsx
        Card.tsx
      layout/
        Container.tsx
        Stack.tsx
    pages/ or routes/
    hooks/
    lib/
    styles/
      index.css   // Tailwind directives + small custom layers
  ```
- Keep design tokens in `tailwind.config` and reusable primitives in `components/ui`.

### 10. Team conventions & code review

- Agree on conventions for:
  - Class order and formatting in JSX.
  - When to create a new component vs. reuse an existing one.
  - When `@apply` is allowed.
- In reviews, look for:
  - Repeated long class strings that should be components.
  - Usage of off-scale values (inline styles, arbitrary values) that break design consistency.
  - Hard-coded colors instead of theme tokens.

### 11. CSS fundamentals still matter

- Tailwind is just a utility API over normal CSS; understanding layout (flex, grid, position, overflow), typography, and cascade is still critical for debugging.
- Use devtools to inspect final computed styles and ensure that Tailwind classes resolve the way you expect.

### 12. Quick checklist for a new component

- Uses semantic HTML and accessible behaviors.
- Uses Tailwind scales (spacing, color, fontSize) instead of ad hoc values.
- Responsive behavior is handled via Tailwind breakpoints.
- Visual variants and sizes are mapped from props to Tailwind class maps.
- No obvious duplication of long class chains across the codebase.
- No unnecessary custom CSS where utilities would suffice.

---

# Project Reference

## What This Project Is

**ScholarSource** — an AI-powered study resource finder. Users submit course info (URL, textbook, ISBN, PDF, or topic list) and a CrewAI multi-agent pipeline searches, validates, and formats supplementary learning resources into a markdown study guide optimized for import into NotebookLM.

---

## Directory Structure

```
scholar_source/
├── backend/                  # FastAPI REST API + Celery worker
├── src/scholar_source/       # CrewAI multi-agent system
│   └── config/               # agents.yaml, tasks.yaml
│   └── tools/                # Custom CrewAI tools
├── web/                      # React + Vite frontend
│   └── src/
│       ├── pages/            # HomePage.jsx
│       ├── components/       # Auth/, ui/, feature components
│       ├── api/client.js     # Supabase + API client
│       └── contexts/         # AuthContext.jsx
├── tests/                    # unit/, integration/, e2e/
├── scripts/                  # Utility + test scripts
├── docs/                     # SDD, TDD, Deployment, Testing docs
├── supabase_schema.sql       # DB schema + RLS policies
├── Procfile.railway          # Railway process definitions
├── nixpacks.toml             # Railway build config (libmagic1)
└── pyproject.toml            # Python project config (version source of truth)
```

---

## Entry Points

| Service | File | Command |
|---------|------|---------|
| Backend API | `backend/main.py` | `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` |
| Celery Worker | `scripts/start_worker.sh` | `./scripts/start_worker.sh` |
| Frontend | `web/src/main.jsx` | `cd web && npm run dev` (port 5173) |
| CrewAI CLI | `src/scholar_source/main.py` | `crewai run` |

---

## Build & Run Commands

```bash
# Backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
./scripts/start_worker.sh             # Celery worker (requires Redis)
# Set SYNC_MODE=true in .env to skip Redis for local dev

# Frontend (from web/)
npm install
npm run dev           # dev server
npm run build         # production build → web/dist
npm run lint          # ESLint
npm test              # Vitest (watch)
npm run test:run      # Vitest (single run)

# Python tests
pytest
pytest tests/unit
pytest tests/integration

# Version sync (web/package.json ← pyproject.toml)
python3 scripts/sync_web_package_version.py
```

---

## Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115.0 |
| Server | Uvicorn (ASGI) |
| AI Agents | CrewAI 0.120.1 |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Search | Serper API + YouTube search tool |
| Database | Supabase (PostgreSQL) via supabase-py 2.9.1 |
| Auth | Supabase JWT + PyJWT 2.9.0 |
| Task Queue | Celery 5.4.0 + Redis 5.2.0 |
| Rate Limiting | SlowAPI 0.1.9 |
| Email | Resend 0.8.0 |
| Validation | Pydantic 2.9.2 |
| Language | Python 3.12 |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 19.2.0 |
| Build | Vite 7.2.4 |
| Styling | Tailwind CSS 3.4.19 |
| Auth/DB Client | @supabase/supabase-js 2.90.1 |
| Testing | Vitest 1.0.0 + React Testing Library + MSW |
| Language | JavaScript/JSX (ES2020+, Node ≥18) |

### Infrastructure
| Component | Platform |
|-----------|----------|
| Frontend | Cloudflare Pages |
| Backend | Railway |
| Database | Supabase (PostgreSQL) |
| Cache/Queue | Redis (Upstash or Redis Cloud) |

---

## Key Backend Modules

| Module | Responsibility |
|--------|----------------|
| `backend/main.py` | Routes: `POST /api/submit`, `GET /api/status/{job_id}`, `GET /api/health` |
| `backend/models.py` | Pydantic request/response models + input sanitization |
| `backend/auth.py` | JWT verification + Supabase user auth |
| `backend/jobs.py` | CRUD for job records in Supabase |
| `backend/crew_runner.py` | Enqueue (Celery) or run (sync) crew jobs |
| `backend/celery_app.py` | Celery + Redis broker config |
| `backend/tasks.py` | Celery task definitions |
| `backend/security_utils.py` | URL validation + prompt injection detection |
| `backend/rate_limiter.py` | Redis-backed or in-memory rate limiting |
| `backend/markdown_parser.py` | Parse crew JSON output → markdown |
| `backend/email_service.py` | Resend API integration |

## CrewAI Agents (4 sequential)

1. **Course Intelligence Agent** — extracts topics from URL/book/ISBN/PDF
2. **Resource Discovery Agent** — finds 5–7 resources via Serper + YouTube
3. **Resource Validator Agent** — verifies URLs, copyright, NotebookLM compatibility
4. **Output Formatter Agent** — produces student-friendly markdown study guide

Custom tools: `WebPageFetcherTool`, `TOCExtractorTool`

---

## Environment Variables

**Backend (`.env`)** — key vars:
```
ENVIRONMENT=local
OPENAI_API_KEY=...
SERPER_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...
REDIS_URL=redis://localhost:6379/0
SYNC_MODE=false          # true = no Redis needed
ALLOW_IN_MEMORY_RATE_LIMIT=false
LOG_LEVEL=INFO
```

**Frontend (`web/.env.local`)**:
```
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_SEARCH_TIMEOUT_MINUTES=5
```

---

## Job Processing Flow

```
Frontend → POST /api/submit
         → job created in Supabase (UUID, "pending")
         → enqueued to Celery/Redis (or runs sync if SYNC_MODE=true)
         → polls GET /api/status/{job_id} every 2s

Celery Worker:
  1. Course Intelligence Agent   (analyze course input)
  2. Resource Discovery Agent    (Serper + YouTube search)
  3. Resource Validator Agent    (verify quality/legality)
  4. Output Formatter Agent      (generate markdown)
  → updates job to "completed" with results JSON + raw_output markdown
```

---

## Key Files Quick Reference

| Need to understand... | Read... |
|----------------------|---------|
| API routes + middleware | `backend/main.py` |
| Request/response shapes | `backend/models.py` |
| Auth flow | `backend/auth.py`, `web/src/contexts/AuthContext.jsx` |
| Agent definitions | `src/scholar_source/crew.py`, `src/scholar_source/config/agents.yaml` |
| Task definitions | `src/scholar_source/config/tasks.yaml` |
| DB schema + RLS | `supabase_schema.sql` |
| Deployment | `Procfile.railway`, `docs/Deployment_Plan.md` |
| Architecture | `docs/scholar_source_SDD.md` |
| Frontend main UI | `web/src/pages/HomePage.jsx` |

