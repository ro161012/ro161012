"""Render the account's live GitHub contribution calendar as local SVG assets."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

API_URL = "https://api.github.com/graphql"
DAYS = 365

QUERY = """
query ContributionCalendar($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_calendar(login: str, token: str) -> tuple[int, list[dict[str, object]]]:
    """Request the public contribution calendar through GitHub GraphQL."""
    now = datetime.now(timezone.utc)
    payload = json.dumps(
        {
            "query": QUERY,
            "variables": {
                "login": login,
                "from": (now - timedelta(days=DAYS)).isoformat(),
                "to": now.isoformat(),
            },
        }
    ).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return int(calendar["totalContributions"]), calendar["weeks"]


def color_for(count: int, light: bool) -> str:
    """Map contribution intensity to a compact, watermark-free heatmap palette."""
    if light:
        palette = ("#ebedf0", "#b8e8ef", "#76d4e3", "#369fbd", "#246b93")
    else:
        palette = ("#252a32", "#123d4a", "#12667a", "#168aa3", "#48c9e7")
    if count <= 0:
        return palette[0]
    if count <= 2:
        return palette[1]
    if count <= 5:
        return palette[2]
    if count <= 9:
        return palette[3]
    return palette[4]


def render_svg(login: str, total: int, weeks: list[dict[str, object]], light: bool) -> str:
    """Generate a self-contained SVG used directly by the profile README."""
    cell, gap, left, top = 10, 3, 38, 34
    width = left + len(weeks) * (cell + gap) + 12
    height = top + 7 * (cell + gap) + 22
    background = "#f7f8fa" if light else "#10141a"
    primary = "#293340" if light else "#d6e3ed"
    secondary = "#64748b" if light else "#8fa3b5"
    labels = ("Mon", "Wed", "Fri")
    label_svg = "".join(
        f'<text x="4" y="{top + (index + 1) * (cell + gap) - 3}" class="sub">{label}</text>'
        for index, label in zip((0, 2, 4), labels)
    )
    cells: list[str] = []
    for week_index, week in enumerate(weeks):
        for day_index, day in enumerate(week["contributionDays"]):
            count = int(day["contributionCount"])
            date = escape(str(day["date"]))
            x = left + week_index * (cell + gap)
            y = top + day_index * (cell + gap)
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{color_for(count, light)}"><title>{date}: {count} contributions</title></rect>'
            )
    title = f"{total} contributions in the last year"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <rect width="100%" height="100%" rx="8" fill="{background}"/>
  <text x="8" y="17" class="title">{escape(title)}</text>
  <text x="{width - 8}" y="17" class="sub" text-anchor="end">{escape(login)}</text>
  <style>.title{{font:600 11px system-ui,Segoe UI,sans-serif;fill:{primary}}}.sub{{font:10px system-ui,Segoe UI,sans-serif;fill:{secondary}}}</style>
  {label_svg}
  {''.join(cells)}
</svg>
'''


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("PROFILE_LOGIN", "ro161012")
    total, weeks = fetch_calendar(login, token)
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.joinpath("profile-heatmap-dark.svg").write_text(render_svg(login, total, weeks, False))
    assets.joinpath("profile-heatmap-light.svg").write_text(render_svg(login, total, weeks, True))
    print(f"Rendered {total} contributions across {len(weeks)} weeks.")


if __name__ == "__main__":
    main()
