#!/usr/bin/env python3
"""Generate profile SVG cards using only GitHub's official REST API.
No third-party stats services or Python dependencies are used.
"""
import json
import os
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GITHUB_USERNAME", "Debanjan-Mondal")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path("assets")
OUT.mkdir(exist_ok=True)


def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-native-stats",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({exc.code}) for {url}: {detail}") from exc


def xml_text(value):
    return escape(str(value))


def text(x, y, value, size=14, fill="#c9d1d9", weight=400):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" fill="{fill}" font-weight="{weight}">{xml_text(value)}</text>'


def card_start(width, height, title):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="12" fill="#1a1b27" stroke="#414868"/>',
        text(24, 34, title, 18, "#c0caf5", 700),
        '<line x1="24" y1="48" x2="%d" y2="48" stroke="#414868"/>' % (width - 24),
    ]


def write_svg(filename, lines):
    lines.append("</svg>")
    (OUT / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    profile = github_get(f"https://api.github.com/users/{USERNAME}")
    repos = []
    page = 1
    while page <= 10:
        batch = github_get(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=owner&sort=updated"
        )
        if not batch:
            break
        repos.extend(r for r in batch if not r.get("fork", False))
        if len(batch) < 100:
            break
        page += 1

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    language_counts = Counter(r.get("language") for r in repos if r.get("language"))
    popular = sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0), r.get("updated_at", "")), reverse=True)[:5]

    # Main profile statistics card. Counts are from GitHub's official REST API.
    lines = card_start(620, 205, f"{USERNAME} · GitHub Overview")
    stats = [
        (28, 88, "Public repositories", profile.get("public_repos", 0)),
        (322, 88, "Followers", profile.get("followers", 0)),
        (28, 145, "Stars on owned repos", stars),
        (322, 145, "Forks of owned repos", forks),
    ]
    for x, y, label, value in stats:
        lines.append(text(x, y, label, 12, "#a9b1d6"))
        lines.append(text(x, y + 27, f"{value:,}", 22, "#7aa2f7", 700))
    lines.append(text(28, 185, "Generated with GitHub's official REST API", 10, "#565f89"))
    write_svg("github-stats.svg", lines)

    # Languages are based on each owned non-fork repo's primary language field.
    total = sum(language_counts.values()) or 1
    lines = card_start(620, 245, "Languages across owned repositories")
    palette = ["#7aa2f7", "#9ece6a", "#e0af68", "#bb9af7", "#f7768e", "#2ac3de", "#ff9e64", "#c0caf5"]
    top_langs = language_counts.most_common(8)
    if not top_langs:
        lines.append(text(24, 85, "No public repository language data available yet.", 13))
    else:
        bar_x, bar_y, bar_w, bar_h = 24, 70, 572, 12
        cursor = bar_x
        for i, (lang, count) in enumerate(top_langs):
            segment = bar_w * count / total
            lines.append(f'<rect x="{cursor:.2f}" y="{bar_y}" width="{max(segment, 1):.2f}" height="{bar_h}" rx="3" fill="{palette[i % len(palette)]}"/>')
            cursor += segment
        for i, (lang, count) in enumerate(top_langs):
            y = 112 + i * 22
            color = palette[i % len(palette)]
            pct = count / total * 100
            lines.append(f'<circle cx="30" cy="{y - 4}" r="4" fill="{color}"/>')
            lines.append(text(43, y, lang, 12, "#c9d1d9"))
            lines.append(text(560, y, f"{pct:.1f}%", 12, "#a9b1d6"))
    write_svg("github-languages.svg", lines)

    # This deliberately says "Popular Repositories", not "Top Contributed Repo":
    # the public REST API's repo list does not provide a trustworthy contribution ranking.
    lines = card_start(620, 265, "Popular Public Repositories")
    if not popular:
        lines.append(text(24, 82, "No public repositories found.", 13))
    else:
        for i, repo in enumerate(popular):
            y = 82 + i * 35
            name = repo.get("name", "repository")
            desc = (repo.get("description") or "No description provided").strip()
            if len(desc) > 62:
                desc = desc[:59] + "..."
            lines.append(text(24, y, name, 13, "#7aa2f7", 700))
            lines.append(text(24, y + 16, desc, 10, "#a9b1d6"))
            meta = f"★ {repo.get('stargazers_count', 0)}   Forks {repo.get('forks_count', 0)}"
            lines.append(text(445, y, meta, 10, "#c0caf5"))
    write_svg("popular-repositories.svg", lines)

    print(f"Generated {len(list(OUT.glob('*.svg')))} SVG cards for {USERNAME} at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
