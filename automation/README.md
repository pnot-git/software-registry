# Weekly check

`scripts/check_registry.py` reads `registry/master-registry.json` and, for each GitHub-hosted record, calls the official GitHub REST API:

- repository status (archived, renamed or moved, unavailable)
- latest release (GitHub Releases; falls back to the newest stable-looking version tag when a project publishes none)
- published security advisories (newest date, and any published in the last 8 days)

It writes `reports/weekly-YYYY-MM-DD.md` and `reports/state.json`. The workflow `.github/workflows/weekly-check.yml` runs every Monday, commits the report, and opens an issue if something needs review. GitHub emails you about new issues in your own repository according to your notification settings.

Result meanings: `not found` means HTTP 404 (could be deleted, private, or renamed: verify manually); `rate limited` and `temporary error` are retried and never reported as deletion.

Known limitations:

- Tag fallback picks the highest numeric version among the first 300 tags (pre-release-looking tags skipped). Results marked `(tag)` can be wrong for repos with unusual tag schemes or more than 300 tags. Treat them as a hint and confirm on the project's own site.
- Node.js does not use GitHub Releases; the script reads nodejs.org/dist/index.json instead.
- Advisory data only covers advisories published on GitHub. Not every project uses them.
- A new release is information, not an instruction to upgrade.

Permissions: the built-in workflow token (`contents: write`, `issues: write`). No personal access token is needed, so there is nothing to revoke.
