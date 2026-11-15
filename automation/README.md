# Weekly check

`scripts/check_registry.py` reads `registry/master-registry.json` and, for each GitHub-hosted record, calls the official GitHub REST API:

- repository status (archived, renamed or moved, unavailable)
- latest stable release
- published security advisories (best effort)

It writes `reports/weekly-YYYY-MM-DD.md`. The workflow `.github/workflows/weekly-check.yml` runs it every Monday and commits the report. If anything needs review, it opens an issue; GitHub emails you about new issues in your own repository if your notification settings allow it.

Result meanings: `not found` means HTTP 404 (could be deleted, private, or renamed: verify manually); `rate limited` and `temporary error` are retried and never reported as deletion.

Permissions: the built-in workflow token (`contents: write`, `issues: write`). No personal access token is needed, so there is nothing to revoke.

Status: written but not yet executed. Run the workflow manually once (Actions tab, Run workflow) and check the result.
