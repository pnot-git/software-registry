# Source-code preservation plan (proposal for review)

Nothing here has been run. No downloads have been started. Sizes below come from the GitHub API `size` field for each repository (kilobytes on GitHub's servers; a local mirror will be roughly similar), checked 2026-11-15.

## Key fact

A deleted repository cannot reliably be forked afterwards. Preservation has to happen beforehand.

## Layers

1. Discovery: stars and Star Lists. Cheap, but preserve nothing.
2. Early warning: release-only watches on critical projects, plus the weekly check in `automation/`.
3. Local bare Git mirrors for chosen projects (`git clone --mirror`, refreshed with `git remote update --prune`).
4. Optional GitHub forks for a very small set of high-priority projects. A fork is not an independent backup, and needs syncing. If upstream is deleted, forks usually survive, but you depend on GitHub.
5. Content Git does not capture: release assets, Git LFS objects, wikis (separate `.wiki.git` repos), issues, pull requests, discussions. Back these up only for projects where they matter; each needs its own export method.

## Proposed scope (decision needed)

Critical-candidate projects total about 24.0 GB including OpenClaw, or about 9.7 GB without it. OpenClaw alone is about 14.3 GB.

| Project | Size (GB) |
|---|---|
| openclaw/openclaw | 14.31 |
| BerriAI/litellm | 2.86 |
| grafana/grafana | 2.05 |
| NousResearch/hermes-agent | 1.39 |
| postgres/postgres | 0.78 |
| n8n-io/n8n | 0.78 |
| paperclipai/paperclip | 0.53 |
| hashicorp/terraform | 0.35 |
| prometheus/prometheus | 0.28 |
| moby/moby | 0.27 |
| redis/redis | 0.21 |
| tailscale/tailscale | 0.09 |
| modelcontextprotocol/servers | 0.03 |
| docker/compose | 0.03 |
| caddyserver/caddy | 0.02 |
| pgvector/pgvector | 0.00 |
| crystaldba/postgres-mcp | 0.00 |
| NousResearch/hermes-paperclip-adapter | 0.00 |

Suggested starting point: mirror the critical candidates except OpenClaw, then decide on OpenClaw separately.

## Platforms

- GitHub: `git clone --mirror`.
- GitLab (GNOME, XFCE, freedesktop) and Debian Salsa: same Git commands work on public repositories.
- Hosts such as git.kernel.org or git.netfilter.org: also plain Git.
- Where a GitHub repo is only a mirror, mirror the real upstream instead.

## Licences and redistribution

Keeping a private local mirror for your own use is generally fine. Publishing forks or redistributing code is governed by each project's licence. Several projects here report `NOASSERTION` from GitHub or have source-available terms (n8n, Terraform, Redis history), so read the licence before publishing a fork. This is not legal advice.

## Freshness and restore

- Freshness: record the date of the last successful `git remote update` per mirror; flag any mirror not updated for 30 days.
- Restore: `git clone <mirror-path> restored-project`, then check out a release tag.
- Test one restore before relying on the setup.

## When an upstream goes missing

1. Check whether it was renamed or moved (search the new owner/org, check the project website).
2. A 404 can also mean private, transferred, or a temporary outage. Wait and recheck before acting.
3. Only after confirming deletion, restore from your mirror or a fork, and document where it now lives.

## Next decision

Choose the mirror destination (a local disk path you control) and the project list. Do not point this at any private server without deciding the destination first.
