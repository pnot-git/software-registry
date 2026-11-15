#!/usr/bin/env python3
"""Weekly check of GitHub-hosted records in registry/master-registry.json.

Uses only the official GitHub REST API. Never upgrades anything. Never treats
a 404, rate limit, or server error as proof of deletion.
"""
import datetime, json, os, sys, time, urllib.error, urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODAY = datetime.date.today().isoformat()


def get(path, retries=3):
    """Return (kind, data, final_url). kind: ok | not_found | forbidden | rate_limited | error."""
    url = API + path
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "software-registry-check",
            **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # redirects followed
                return "ok", json.load(r), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "not_found", None, url
            if e.code in (403, 429):
                if e.headers.get("X-RateLimit-Remaining") == "0" or e.code == 429:
                    reset = int(e.headers.get("X-RateLimit-Reset", "0"))
                    wait = min(max(reset - time.time(), 1), 60)
                    if attempt < retries - 1:
                        time.sleep(wait)
                        continue
                    return "rate_limited", None, url
                return "forbidden", None, url
            if e.code >= 500 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return "error", "HTTP %s" % e.code, url
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return "error", str(e), url
    return "error", "unknown", url


def main():
    reg = json.load(open(os.path.join(ROOT, "registry", "master-registry.json")))["records"]
    state_path = os.path.join(ROOT, "reports", "state.json")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    new_state, findings, rows = {}, [], []

    for r in reg:
        repo = r["github_repo"]
        if not repo or r["platform"] == "n/a":
            continue
        kind, data, final = get("/repos/" + repo)
        entry = {"id": r["id"], "repo": repo, "release": None}
        if kind != "ok":
            label = {"not_found": "not found (404: deleted, private, or renamed; verify manually)",
                     "forbidden": "permission failure (403)",
                     "rate_limited": "rate limited (not a repository problem)",
                     "error": "temporary error: %s" % data}[kind]
            rows.append("| %s | %s | %s |" % (r["id"], repo, label))
            findings.append("%s: %s" % (repo, label))
            if repo in state:
                new_state[repo] = state[repo]
            continue
        if data["full_name"].lower() != repo.lower():
            findings.append("%s moved/renamed to %s" % (repo, data["full_name"]))
        if data.get("archived") and r.get("archived") is not True:
            findings.append("%s is now ARCHIVED" % repo)
        k2, rel, _ = get("/repos/%s/releases/latest" % data["full_name"])
        tag = rel["tag_name"] if k2 == "ok" else None  # /latest excludes drafts and prereleases
        prev = state.get(repo, {}).get("release")
        if tag and prev and tag != prev:
            findings.append("%s: new release %s (was %s)" % (repo, tag, prev))
        new_state[repo] = {"release": tag or prev}
        k3, adv, _ = get("/repos/%s/security-advisories?state=published&per_page=3" % data["full_name"])
        n_adv = len(adv) if k3 == "ok" and isinstance(adv, list) else "n/a"
        rows.append("| %s | %s | latest release: %s | advisories (latest 3): %s |" % (r["id"], repo, tag or "none/unknown", n_adv))

    report = ["# Weekly check %s" % TODAY, "", "## Needs review", ""]
    report += ["- " + f for f in findings] or ["- Nothing flagged."]
    report += ["", "## All checked", "", "| ID | Repo | Result |  |", "|---|---|---|---|"] + rows
    report += ["", "A new release is information, not an instruction to upgrade."]
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    path = os.path.join(ROOT, "reports", "weekly-%s.md" % TODAY)
    open(path, "w").write("\n".join(report) + "\n")
    json.dump(new_state, open(state_path, "w"), indent=1)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write("flagged=%s\n" % ("true" if findings else "false"))
    print(path, "findings:", len(findings))


if __name__ == "__main__":
    sys.exit(main())
