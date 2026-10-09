"""Refresh both profile languages from public GitHub activity only."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import argparse
import html
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
USER = "GhostDragon9889"
START, END = "<!-- ACTIVITY:START -->", "<!-- ACTIVITY:END -->"
REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


def get_json(path):
    headers = {"User-Agent": "GhostDragon-profile-activity", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
    token = os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # The API origin is fixed. No repository data controls the request host.
    request = Request("https://api.github.com/" + path, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code in (403, 404) and token:
            headers.pop("Authorization", None)
            with urlopen(Request(request.full_url, headers=headers), timeout=30) as response:
                return json.load(response)
        raise


def public_pushes(events, user=USER):
    pushes, seen = [], set()
    for event in sorted(events, key=lambda e: e.get("created_at", ""), reverse=True):
        repo = event.get("repo", {}).get("name", "")
        if (event.get("type") != "PushEvent" or event.get("public") is not True
                or event.get("actor", {}).get("login", "").lower() != user.lower()
                or not REPO_PATTERN.fullmatch(repo) or not event.get("created_at")):
            continue
        key = event.get("id")
        if not key or key in seen:
            continue
        seen.add(key)
        payload = event.get("payload", {})
        ref = payload.get("ref", "")
        branch = ref.removeprefix("refs/heads/").removeprefix("refs/tags/") or "default"
        base = f"https://github.com/{repo}"
        head, before = payload.get("head", ""), payload.get("before", "")
        url = base + "/commits/" + quote(branch, safe="")
        if SHA_PATTERN.fullmatch(head):
            url = base + "/commit/" + head
            if SHA_PATTERN.fullmatch(before) and before != "0" * 40:
                url = base + "/compare/" + before + "..." + head
        pushes.append({"id": key, "repo": repo, "branch": branch, "date": event["created_at"], "url": url})
    return pushes[:5]


def normalize_commit(commit, repo, user=USER):
    if (not REPO_PATTERN.fullmatch(repo) or not SHA_PATTERN.fullmatch(commit.get("sha", ""))
            or (commit.get("author") or {}).get("login", "").lower() != user.lower()):
        return None
    data = commit.get("commit", {})
    date = (data.get("committer") or {}).get("date")
    if not date:
        return None
    return {"repo": repo, "sha": commit["sha"], "date": date,
            "message": data.get("message", "").splitlines()[0] if data.get("message") else "Commit",
            "url": f"https://github.com/{repo}/commit/{commit['sha']}"}


def candidate_repos(public_repos, pushes):
    available = {r["full_name"] for r in public_repos}
    selected = [f"{USER}/{name}" for name in [USER, "IsaacLab_Walker_S2", "Simulation", f"{USER}.github.io"]
                if f"{USER}/{name}" in available]
    return list(dict.fromkeys([p["repo"] for p in pushes] + selected + [r["full_name"] for r in public_repos]))[:10]


def collect():
    events = []
    for page in range(1, 4):
        batch = get_json(f"users/{USER}/events/public?per_page=100&page={page}")
        events.extend(batch)
        if len(batch) < 100:
            break
    pushes = public_pushes(events)
    repos = get_json(f"users/{USER}/repos?" + urlencode({"type": "owner", "sort": "pushed", "per_page": 100}))
    public_repos = [r for r in repos if r.get("private") is False and REPO_PATTERN.fullmatch(r.get("full_name", ""))]
    names = candidate_repos(public_repos, pushes)
    commits = []
    for repo in names:
        try:
            batch = get_json(f"repos/{repo}/commits?" + urlencode({"author": USER, "per_page": 5}))
        except HTTPError as error:
            if error.code in (404, 409):  # Deleted/inaccessible or empty public repository.
                continue
            raise
        commits.extend(c for raw in batch if (c := normalize_commit(raw, repo)))
    commits.sort(key=lambda c: c["date"], reverse=True)
    seen, unique = set(), []
    for commit in commits:
        if commit["sha"] not in seen:
            unique.append(commit)
            seen.add(commit["sha"])
    return {"pushes_available": True, "pushes": pushes, "commits": unique[:5]}


def local_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")


def escape(value):
    escaped = html.escape(str(value), quote=True)
    return re.sub(r"([\\`*_\[\]|])", r"\\\1", escaped).replace("\n", " ").replace("\r", " ")


def render(data, language):
    zh = language == "zh"
    stamp = local_time(data["updated_at"])
    note = "公开活动 · 更新于" if zh else "Public activity · Updated"
    lines = [f"<sub>{note} {stamp} (UTC+8). " + ("每 6 小时检查更新；推送事件可能延迟。" if zh else "Checked every 6 hours; push events may be delayed.") + "</sub>", ""]
    lines += ["### 最近提交" if zh else "### Recent Commits", ""]
    lines += ["来自代表项目与近期活跃的公开仓库。" if zh else "From selected projects and recently active public repositories.", ""]
    for commit in data["commits"]:
        lines += [f"- **[{commit['sha'][:7]}]({commit['url']})** · {escape(commit['repo'])}",
                  f"  <sub>{local_time(commit['date'])} · {html.escape(commit['message'][:90])}</sub>"]
    if not data["commits"]:
        lines.append("暂未检索到提交记录。" if zh else "No commits found in the scanned public repositories.")
    lines += ["", "### 最近推送" if zh else "### Recent Pushes", ""]
    if not data.get("pushes_available"):
        lines.append("首次活动更新完成后显示推送记录。" if zh else "Push records will appear after the first activity refresh.")
    elif not data["pushes"]:
        lines.append("最近的公开事件中暂无推送记录。" if zh else "No pushes found in the recent public event window.")
    for push in data["pushes"]:
        lines += [f"- **[{escape(push['repo'])}]({push['url']})** · {escape(push['branch'])}", f"  <sub>{local_time(push['date'])} (UTC+8)</sub>"]
    return "\n".join(lines)


def update_files(root, activity, now=None):
    cache = root / "activity-data.json"
    old = json.loads(cache.read_text()) if cache.exists() else None
    comparable = {k: old.get(k) for k in activity} if old else None
    snapshot = old if comparable == activity else {**activity, "updated_at": now or datetime.now(timezone.utc).isoformat(timespec="seconds")}
    changes = []
    # Validate both markers before writing either language.
    for filename, lang in [("README.md", "en"), ("README.zh-CN.md", "zh")]:
        path = root / filename
        source = path.read_text()
        if source.count(START) != 1 or source.count(END) != 1 or source.index(START) > source.index(END):
            raise ValueError(f"Invalid activity markers in {filename}")
        prefix, rest = source.split(START, 1)
        _, suffix = rest.split(END, 1)
        result = prefix + START + "\n" + render(snapshot, lang) + "\n" + END + suffix
        if result != source:
            changes.append((path, result))
    for path, result in changes:
        path.write_text(result)
    if old != snapshot:
        cache.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    return bool(changes or old != snapshot)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, help="Render an already verified local snapshot without API requests")
    args = parser.parse_args()
    if args.snapshot:
        source = json.loads(args.snapshot.read_text())
        activity = {k: source[k] for k in ["pushes_available", "pushes", "commits"]}
        changed = update_files(ROOT, activity, source.get("updated_at"))
    else:
        changed = update_files(ROOT, collect())
    print("Activity updated." if changed else "Activity unchanged.")


if __name__ == "__main__":
    main()
