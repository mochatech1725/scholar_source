# Baseline Run Summary

## Purpose

This summary supports Phase 0.1 of the ScholarSource v2 implementation plan: run v1 multiple times with the same input and capture what changes.

## Source Log

Local Railway API export:

`/Users/teial/Downloads/logs.1782856742076.json`

Local Railway worker exports:

`/Users/teial/Downloads/logs.1782858395047.log`

`/Users/teial/Downloads/logs.1782858386344.json`

Local Railway production API export:

`/Users/teial/Downloads/scholar-source-prod.1783025385198.log`

Local Railway production worker export:

`/Users/teial/Downloads/scholar-source-celery.prod.1783025609450.log`

The API export contains 163 log entries. Four same-input job submissions were visible in the extracted API logs.

The worker log contains 3,651 lines and includes Celery task execution, CrewAI task transitions, tool calls, search queries, final answer excerpts, and job completion records.

The production API export contains 334 log lines. It shows an additional same-input production submission for job `cb4832bb-eaa7-4e1b-8dc5-9c1f75bd8e1a` at 2026-06-30 21:13:54 UTC and a Celery enqueue event with task ID `33958c7a-9b05-45d7-a94b-a916bf48a00a`.

The production worker export contains 10,090 log lines. It confirms job `cb4832bb-eaa7-4e1b-8dc5-9c1f75bd8e1a` started CrewAI execution, used the same course URL input, completed CrewAI execution, and completed successfully with 5 resources.

## Same Input Used

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

No textbook, topic list, ISBN, chapter, targeted sites, excluded sites, or preferred creators were submitted.

## Runs Found

| Run | Submitted At | Job ID | Celery Task ID | Outcome | Elapsed |
| --- | --- | --- | --- | --- | --- |
| 1 | 2026-06-30 21:13:54 UTC | `cb4832bb-eaa7-4e1b-8dc5-9c1f75bd8e1a` | `33958c7a-9b05-45d7-a94b-a916bf48a00a` | Completed with 5 reported resources | 68.75s |
| 2 | 2026-06-30 21:14:05 UTC | `6647547c-43d3-4f93-a06b-4aa6eb988793` | `e0387baf-1ae3-4730-999d-427edda80b35` | Completed with 5 reported resources | 72.31s |
| 3 | 2026-06-30 21:44:48 UTC | `8f2e7e19-b1ca-479b-ba0b-b4bedb3e1dbc` | `891270b0-9519-4fc7-9a0b-8386c1109f27` | Completed with 6 reported resources | 61.12s |
| 4 | 2026-06-30 21:46:49 UTC | `180d3cc7-eaa5-49a4-8acf-5892b6555046` | `a98ecfed-c5c0-4d36-a1da-7330b04de2bb` | Completed with 5 reported resources | 48.90s |
| 5 | 2026-06-30 21:54:50 UTC | `fc826ef4-2752-4bd1-965b-7cf438caf0d5` | `28b59c48-38a7-4d18-b721-b40ef201ecce` | Completed with 5 reported resources | 46.69s |

## What Changed Across Runs

- Job ID changed each run, as expected.
- Celery task ID changed each run, as expected.
- Submission input appears identical across the five visible completed runs.
- Run 1 logged a warning that no Celery workers were available, then later logged enqueue activity.
- Generated search queries changed across runs.
- The resource search agent used different numbers of Serper searches across runs.
- Final reported resource counts changed across runs.
- Visible final source domains changed across runs.
- Final output formatting varied, including headings, emoji usage, and resource-count wording.

## Search Query Variation

Examples visible in the worker log:

| Run | Visible Search Query |
| --- | --- |
| 1 | `Engineering Mechanics Statics practice exam PDF site:edu` |
| 2 | `Engineering Mechanics practice exam site:edu` |
| 3 | `Engineering mechanics statics exam pdf site:edu` and `engineering mechanics statics practice exams pdf site:edu` |
| 4 | `Engineering Mechanics Statics exam problems PDF site:edu` |

This is a major finding. The same submitted course URL did not lead to one stable retrieval plan.

## Resource Variation

Visible final-output snippets show different selected resources:

- Run 1 includes Purdue, SUNY, and Lafayette-style resources in the visible final output.
- Run 2 includes MIT OpenCourseWare, Perry Tech, Syracuse, and Purdue-style resources in the visible final output.
- Run 3 includes NJIT digitalcommons resources in the visible final output.
- Run 4 reports four validated resources, with search results beginning from Purdue and Colorado Mesa-style resources.

Because Railway wraps long final-output lines, exact URL comparison should be done from stored job results if available. The log is still enough to prove that the resource set was not stable.

## Most Likely Current Conclusion

These logs prove repeated same-input submissions reached the API and queue layer, then entered full CrewAI execution.

The most likely source of v1 inconsistency is the agentic retrieval harness: the resource search agent makes different search-planning decisions for the same input, which leads to different search queries, different candidate resources, different validation inputs, and different final outputs.

## Diagnostic Value

The API log establishes that the instability is not caused by different submitted inputs. The worker log shows the variation happening after job processing begins, especially in agent reasoning and search.

## Follow-Up Evidence To Capture

- Stored final output for each job ID.
- Clean discovered source URLs for each job ID.
- Validation pass and rejection reasons for each source.
- Final markdown or JSON result from the database for each job.
- Railway service metadata showing whether these logs came from the dev or production deployment.

## Extra Observation

The worker log also includes an earlier job, `edea20b3-a1a8-48db-a4f7-b9858bb05f61`, that was cancelled before execution. It is not counted as one of the four baseline runs because it did not execute the CrewAI pipeline.
