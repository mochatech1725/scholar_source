# React and Tailwind Guidelines

## Core React Patterns

- Prefer **functional** components and Hooks; treat class components as legacy unless integrating with old code.
- Keep components small, focused, and single-responsibility; if a component grows beyond ~150–200 lines or handles several concerns, split it.
- Co-locate logic with the component that owns it (state, derived data, effects, queries) instead of scattering utilities and hooks across the app.
- Use composition over inheritance: accept children/slots instead of deeply nested prop options or config objects.
- Use controlled components for form elements whenever you need validation, instant feedback, or complex interactions; otherwise consider uncontrolled refs for simple cases.

---

## State and Data Fetching

- Keep state as **local** as possible; lift state only when multiple components truly share it.
- Avoid prop drilling across many levels; use Context for cross-cutting concerns and consider a lightweight state library (Zustand, Jotai, Redux Toolkit) for complex global state.
- Store the minimal state needed; derive everything else from props or existing state instead of duplicating values.
- Treat server as the source of truth for server data and client state as a cache or view model.
- Use a dedicated data-fetching library (TanStack Query / React Query or SWR) instead of ad-hoc `useEffect` + fetch for anything beyond trivial requests.
- Normalize async flows: handle loading, error, empty, and success states explicitly and consistently.

---

## React 18 Features and Concurrency

- Use Suspense for data fetching and code-splitting boundaries to improve perceived loading and structure async flows.
- Use concurrent APIs like `useTransition` and `useDeferredValue` to keep the UI responsive during expensive updates or filtering.
- Design UI so that non-critical parts can be deferred or streamed rather than blocking the initial render.

---

## Performance and Rendering

- Minimize unnecessary re-renders:
  - Use `React.memo` for pure presentational components with stable props.
  - Use `useCallback` and `useMemo` for expensive computations or when prop identity matters.
- Avoid inline anonymous functions and object/array literals in hot rendering paths when they cause prop identity churn.
- Use stable, unique keys for list items; never use array index as key when the list can be reordered or filtered.
- Virtualize large lists and tables to avoid rendering hundreds/thousands of DOM nodes.
- Avoid overusing Context; large or frequently changing contexts can trigger expensive tree-wide re-renders.
- Split bundles using dynamic import and `React.lazy` for heavy, rarely used routes or components.

---

## Structure, Organization, and Reuse

- Organize files by feature/module instead of strictly by type; keep components, hooks, and tests for a feature together.
- Extract reusable UI patterns as shared components and shared hooks (e.g., `useForm`, `useModal`, `useFetch`).
- Keep hooks pure; avoid doing non-React side effects directly in custom hooks unless the hook is specifically about that effect.
- Prefer simple, predictable naming: `useFoo` for hooks, `PascalCase` for components, clear prop names instead of abbreviations.

---

## TypeScript and Safety

- Use TypeScript (or at least JSDoc types) for components, hooks, and utilities.
- Prefer typed props and state over `any`/`unknown`; model domain concepts with discriminated unions instead of booleans where multiple states are possible.
- Type external data at the boundary (e.g., API responses), and consider runtime validation for untrusted inputs.

---

## JSX, Styling, and DOM

- Keep JSX clean and readable; avoid deeply nested markup by extracting subcomponents.
- Avoid putting complex logic directly in JSX; move it into variables or helper functions above the `return`.
- Use semantic HTML tags and ARIA attributes; avoid div-soup, especially for interactive elements.
- Prefer Tailwind CSS utility classes co-located in JSX; avoid global styles that leak across features.

---

## Side Effects and Lifecycle

- Use `useEffect` only for real side effects (subscriptions, event listeners, imperative APIs, syncing with non-React systems).
- Carefully manage effect dependencies; prefer making effects idempotent and narrowing their scope.
- Clean up subscriptions, timers, event listeners, and observers in the effect cleanup function.

---

## Error Handling, Boundaries, and UX

- Use Error Boundaries around major app sections (routes, dashboards, complex widgets) to avoid full app crashes.
- Provide meaningful fallbacks for loading and error states (skeletons/spinners + retry, not just blank or generic messages).

---

## Testing and Maintainability

- Write tests for critical flows using Vitest for unit tests and React Testing Library for behavior-focused component tests.
- Favor testing behavior and user-visible outcomes rather than implementation details or specific hook calls.
- Keep strict ESLint + Prettier configs and ensure code always passes lint/format checks.

---

## Tailwind Best Practices

### Project and Config

- Keep all Tailwind setup in `tailwind.config.(js|ts)` and a single main CSS entry (`src/index.css`).
- Extend Tailwind instead of replacing it; add design tokens (colors, spacing, fonts) under `theme.extend`.
- Prefer semantic tokens: `brand`, `accent`, `danger` rather than raw hex names.

### Utility-First Mindset

- Prefer Tailwind utility classes co-located in JSX instead of separate CSS.
- Let Tailwind's scales drive design (spacing, font sizes, colors) rather than arbitrary values.
- Use Tailwind's mobile-first responsive prefixes: `sm:`, `md:`, `lg:`, `xl:`, `2xl:`.

### ClassName Organization

- Group related utilities: layout → spacing → typography → decoration → state variants.
- Use `clsx` or `classnames` and `tailwind-merge` for complex components.
- Avoid passing raw Tailwind className fragments as many small props; prefer higher-level props like `variant`, `size`, `intent`.

### When Not to Use `@apply`

- Prefer pure utilities first; only introduce `@apply` when you repeat long utility chains across many components or need complex selectors.
- Do not use `@apply` for variants like `hover:`/`focus:` — it hides what the component actually does.

### Accessibility and Semantics

- Use proper semantic elements: `<button>`, `<a>`, `<label>`, `<nav>`, `<main>`, etc.
- Always provide `focus:` styles; never remove `outline` without a replacement.
- Ensure color contrast meets WCAG using your design tokens across the app.

### Performance and Bundle Size

- Ensure the `content` option in `tailwind.config` covers all JSX/TSX files so unused classes are purged.
- Avoid constructing class names dynamically with string concatenation that PurgeCSS cannot detect.

### Quick Checklist for a New Component

- Uses semantic HTML and accessible behaviors.
- Uses Tailwind scales (spacing, color, fontSize) instead of ad-hoc values.
- Responsive behavior is handled via Tailwind breakpoints.
- Visual variants and sizes are mapped from props to Tailwind class maps.
- No obvious duplication of long class chains across the codebase.
- No unnecessary custom CSS where utilities would suffice.
