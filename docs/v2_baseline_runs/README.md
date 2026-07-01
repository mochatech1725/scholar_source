# ScholarSource v2 Baseline Runs

This folder captures the Phase 0.1 baseline evidence for repeated v1 runs using the same input.

The first source evidence came from a Railway API JSON log export stored locally at:

`/Users/teial/Downloads/logs.1782856742076.json`

Additional worker-side evidence came from Railway Celery log exports stored locally at:

`/Users/teial/Downloads/logs.1782858395047.log`

`/Users/teial/Downloads/logs.1782858386344.json`

The raw exports were not copied here because they contain Railway project, deployment, replica, user, task, and runtime metadata. These notes preserve the useful diagnostic facts while keeping the docs suitable for version control.

## Input Used

Course URL:

`https://www.mccormick.northwestern.edu/civil-environmental/academics/courses/descriptions/GEN_ENG%20205-2.html`

All observed runs used the same submitted input shape:

- Course name: empty
- University name: empty
- Course URL: present
- Textbook: empty
- Topics list: empty
- Book metadata: empty
- Desired resource types: empty list
- Excluded sites: empty
- Targeted sites: empty
- Chapter and sections: empty
- Preferred creators: empty

## What This Log Proves

- The same query was submitted multiple times.
- Each submission created a distinct job record.
- Each job was enqueued to Celery with a distinct task identifier.
- The frontend repeatedly polled job status after submission.
- One run logged a warning that no Celery workers were available at submission time, but it was later enqueued.
- The worker logs show CrewAI execution for the repeated jobs.
- The worker logs show all four main CrewAI tasks running: course analysis, resource search, resource validation, and final output formatting.
- The worker logs show different generated search queries across same-input runs.
- The worker logs show different Serper search counts across same-input runs.
- The worker logs show different final resource counts across same-input runs.

## What This Log Does Not Prove

- It does not provide a clean machine-readable final result per job.
- Some final output lines are visually wrapped by Railway, so exact URL reconstruction should be done from stored job results rather than terminal-formatted logs.
- It does not prove whether the run came from a production or development deployment without checking Railway service metadata directly.

For diagnosing why v1 returns inconsistent final results, these worker logs are strong enough to show that instability enters during agent execution, especially search planning and resource selection. Stored job results are still useful for exact final-output comparison.
