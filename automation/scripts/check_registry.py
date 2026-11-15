#!/usr/bin/env python3
"""Weekly check of GitHub-hosted records in registry/master-registry.json.

Uses the official GitHub REST API (plus nodejs.org's release index for Node.js).
Never upgrades anything. Never treats a 404, rate limit, or server error as
proof of deletion.
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TODAY = datetime.date.today().isoformat()
ADVISORY_CUTOFF = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
PRE = re.compile(r"(alpha|beta|rc|pre|dev|snapshot|nightly)", re.I)
PRE2 = re.compile(r"\d(a|b)\d+$", re.I)


def get(path, retries=3):
    """Return (kind, data, final_url). kind: ok | not_found | forbidden | rate_limited | error."""
    url = path if path.startswith("http") else API + path
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "software-registry-check"}
    if TOKEN and url.startswith(API):
        headers["Authorization"] = "Bearer " + TOKEN
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
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
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return "error", str(e), url
    return "error", "unknown", url


def vkey(tag):
    return tuple(int(x) for x in re.findall(r"\d+", tag))


def pick_latest_tag(names):
    best = None
    for name in names:
        if not re.search(r"\d", name) or PRE.search(name) or PRE2.search(name):
            continue
        if best is None or vkey(name) > vkey(best):
            best = name
    return best


def latest_tag(full_name):
    """Highest numeric version among up to 300 tags. A hint only, see automation/README.md."""
    names = []
    for page in (1, 2, 3):
        k, data, _ = get("/repos/%s/tags?per_page=100&page=%d" % (full_name, page))
        if k != "ok" or not data:
            break
        names += [t["name"] for t in data]
        if len(data) < 100:
            break
    return pick_latest_tag(names)


def node_versions():
    k, data, _ = get("https://nodejs.org/dist/index.json")
    if k != "ok" or not data:
        return None
    lts = next((d["version"] for d in data if d.get("lts")), None)
    return "%s (latest LTS %s; from nodejs.org)" % (data[0]["version"], lts)


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
        kind, data, _ = get("/repos/" + repo)
        if kind != "ok":
            label = {"not_found": "not found (404: deleted, private, or renamed; verify manually)",
                     "forbidden": "permission failure (403)",
                     "rate_limited": "rate limited (not a repository problem)",
                     "error": "temporary error: %s" % data}[kind]
            rows.append("| %s | %s | %s | | |" % (r["id"], repo, label))
            findings.append("%s: %s" % (repo, label))
            if repo in state:
                new_state[repo] = state[repo]
            continue
        full = data["full_name"]
        if full.lower() != repo.lower():
            findings.append("%s moved/renamed to %s" % (repo, full))
        if data.get("archived") and r.get("archived") is not True:
            findings.append("%s is now ARCHIVED" % repo)

        if repo.lower() == "nodejs/node":
            latest = node_versions() or "unavailable"
        else:
            k2, rel, _ = get("/repos/%s/releases/latest" % full)  # excludes drafts and prereleases
            latest = rel["tag_name"] if k2 == "ok" and rel.get("tag_name") else None
            if not latest:
                t = latest_tag(full)
                latest = (t + " (tag)") if t else "none found"
        prev = state.get(repo, {}).get("release")
        if prev and latest not in ("none found", "unavailable") and latest != prev:
            findings.append("%s: latest changed to %s (was %s)" % (repo, latest, prev))
        new_state[repo] = {"release": latest if latest not in ("none found", "unavailable") else prev}

        k3, adv, _ = get("/repos/%s/security-advisories?state=published&per_page=5" % full)
        newest, recent = "n/a", "n/a"
        if k3 == "ok" and isinstance(adv, list):
            dates = [a["published_at"] for a in adv if a.get("published_at")]
            newest = max(dates)[:10] if dates else "none"
            fresh = [a for a in adv if a.get("published_at") and a["published_at"][:10] >= ADVISORY_CUTOFF]
            recent = str(len(fresh))
            for a in fresh:
                findings.append("%s: advisory %s (%s) published %s" % (
                    repo, a.get("ghsa_id", "?"), a.get("severity", "?"), a["published_at"][:10]))
        rows.append("| %s | %s | %s | %s | %s |" % (r["id"], repo, latest, newest, recent))

    report = ["# Weekly check %s" % TODAY, "", "## Needs review", ""]
    report += ["- " + f for f in findings] or ["- Nothing flagged."]
    report += ["", "## All checked", "",
               "| ID | Repo | Latest release or tag | Newest advisory | Advisories in last 8 days |",
               "|---|---|---|---|---|"] + rows
    report += ["", "A new release is information, not an instruction to upgrade.",
               "Entries marked (tag) are derived from version tags and may be wrong; confirm on the project's site."]
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
