# Baseline Run 03

## Raw Log Source

`/Users/teial/Downloads/logs.1782856742076.json`

`/Users/teial/Downloads/logs.1782858395047.log`

## Job ID

`180d3cc7-eaa5-49a4-8acf-5892b6555046`

## Celery Task ID

`a98ecfed-c5c0-4d36-a1da-7330b04de2bb`

## Input

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

All other optional input fields were empty or unset.

## Timeline Notes

- Job submission request logged at `2026-06-30 21:46:49 UTC`.
- Job record created at `2026-06-30 21:46:49 UTC`.
- Job enqueue logged at `2026-06-30 21:46:51 UTC`.
- Celery task identifier logged at `2026-06-30 21:46:51 UTC`.
- Frontend status polling is visible after submission.
- Celery worker started this job at `2026-06-30 21:46:51 UTC`.
- CrewAI execution completed at `2026-06-30 21:47:40 UTC`.
- Job completed successfully with 5 reported resources after 48.90 seconds.

## Agent Flow

Visible in the worker log:

- Course analysis completed.
- Resource search completed.
- Resource validation completed.
- Final output formatting completed.
- Resource search used Serper twice.
- Visible generated search queries include `Engineering mechanics statics exam pdf site:edu` and `engineering mechanics statics practice exams pdf site:edu`.

## Final Output

Visible in the worker log as wrapped markdown.

The final output reports `Total Resources Count: 4`, while the job completion log reports `resource_count: 5`.

Visible source snippets include NJIT digitalcommons resources.

## Difference Notes

This run used two similar but distinct statics exam searches and selected a visibly different resource set from Runs 1 and 2.
