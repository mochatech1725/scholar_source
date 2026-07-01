# Baseline Run 04

## Raw Log Source

`/Users/teial/Downloads/logs.1782856742076.json`

`/Users/teial/Downloads/logs.1782858395047.log`

## Job ID

`fc826ef4-2752-4bd1-965b-7cf438caf0d5`

## Celery Task ID

`28b59c48-38a7-4d18-b721-b40ef201ecce`

## Input

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

All other optional input fields were empty or unset.

## Timeline Notes

- Job submission request logged at `2026-06-30 21:54:50 UTC`.
- Job record created at `2026-06-30 21:54:50 UTC`.
- Job enqueue logged at `2026-06-30 21:54:52 UTC`.
- Celery task identifier logged at `2026-06-30 21:54:52 UTC`.
- Frontend status polling is visible after submission.
- Celery worker started this job at `2026-06-30 21:54:52 UTC`.
- CrewAI execution started at `2026-06-30 21:54:52 UTC`.
- CrewAI execution completed at `2026-06-30 21:55:38 UTC`.
- Job completed successfully with 5 reported resources after 46.69 seconds.

## Agent Flow

Visible in the worker log:

- Course analysis completed.
- Resource search completed.
- Resource validation completed.
- Final output formatting completed.
- Resource search used Serper once.
- Visible generated search query: `Engineering Mechanics Statics exam problems PDF site:edu`.

## Final Output

Visible in the worker log as wrapped markdown.

The final output reports `Total Validated Resources: 4`, while the job completion log reports `resource_count: 5`.

## Difference Notes

This run is the fastest successful baseline run and uses a different search query from the other same-input runs.
