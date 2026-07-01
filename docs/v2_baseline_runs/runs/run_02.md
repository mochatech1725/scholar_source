# Baseline Run 02

## Raw Log Source

`/Users/teial/Downloads/logs.1782856742076.json`

`/Users/teial/Downloads/logs.1782858395047.log`

## Job ID

`8f2e7e19-b1ca-479b-ba0b-b4bedb3e1dbc`

## Celery Task ID

`891270b0-9519-4fc7-9a0b-8386c1109f27`

## Input

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

All other optional input fields were empty or unset.

## Timeline Notes

- Job submission request logged at `2026-06-30 21:44:48 UTC`.
- Job record created at `2026-06-30 21:44:49 UTC`.
- Job enqueue logged at `2026-06-30 21:44:51 UTC`.
- Celery task identifier logged at `2026-06-30 21:44:51 UTC`.
- Frontend status polling is visible after submission.
- Celery worker started this job at `2026-06-30 21:44:51 UTC`.
- CrewAI execution started at `2026-06-30 21:44:52 UTC`.
- CrewAI execution completed at `2026-06-30 21:45:52 UTC`.
- Job completed successfully with 6 reported resources after 61.12 seconds.

## Agent Flow

Visible in the worker log:

- Course analysis completed.
- Resource search completed.
- Resource validation completed.
- Final output formatting completed.
- Resource search used Serper twice.
- Visible generated search query: `Engineering Mechanics practice exam site:edu`.

## Final Output

Visible in the worker log as wrapped markdown.

Visible source snippets include MIT OpenCourseWare, Perry Tech, Syracuse, and Purdue-style resources.

## Difference Notes

The search query is broader than Run 1 because it drops `Statics` and `PDF`. This appears to contribute to a different resource set and a different reported resource count.
