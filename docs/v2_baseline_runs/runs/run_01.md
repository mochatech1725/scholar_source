# Baseline Run 01

## Raw Log Source

`/Users/teial/Downloads/logs.1782856742076.json`

`/Users/teial/Downloads/logs.1782858395047.log`

## Job ID

`6647547c-43d3-4f93-a06b-4aa6eb988793`

## Celery Task ID

`e0387baf-1ae3-4730-999d-427edda80b35`

## Input

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

All other optional input fields were empty or unset.

## Timeline Notes

- Job submission request logged at `2026-06-30 21:14:05 UTC`.
- Job record created at `2026-06-30 21:14:06 UTC`.
- Worker availability warning logged at `2026-06-30 21:14:08 UTC`.
- Job enqueue logged at `2026-06-30 21:14:10 UTC`.
- Celery task identifier logged at `2026-06-30 21:14:10 UTC`.
- Frontend status polling is visible after submission.
- Celery worker started this job at `2026-06-30 21:14:10 UTC`.
- CrewAI execution started at `2026-06-30 21:14:11 UTC`.
- CrewAI execution completed at `2026-06-30 21:15:22 UTC`.
- Job completed successfully with 5 reported resources after 72.31 seconds.

## Agent Flow

Visible in the worker log:

- Course analysis completed.
- Resource search completed.
- Resource validation completed.
- Final output formatting completed.
- Resource search used Serper once.
- Visible generated search query: `Engineering Mechanics Statics practice exam PDF site:edu`.

## Final Output

Visible in the worker log as wrapped markdown.

The final output reports `Total Resources: 4`, while the job completion log reports `resource_count: 5`.

Visible source snippets include Purdue, SUNY, and Lafayette-style resources.

## Difference Notes

This run is the only visible run with a worker availability warning before enqueue. It was also the slowest successful run.

The visible generated search query differs from the later same-input runs.
