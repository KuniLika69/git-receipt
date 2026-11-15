#!/usr/bin/env python3
"""Print a receipt from local Git history."""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def read_history(repo: Path, since: str) -> tuple[int, int, int, int]:
    result = subprocess.run(
        [
            "git", "-C", str(repo), "--no-pager", "log", "HEAD",
            "--no-merges", "--no-renames", "--no-ext-diff", "--no-textconv",
            "--no-notes", "--no-show-signature", "--no-color",
            "--format=%H", "--numstat", "-z", f"--since-as-filter={since}", "--",
        ],
        capture_output=True,
        check=True,
    )
    commits = added = removed = 0
    paths = set()
    for entry in result.stdout.split(b"\0"):
        entry = entry.lstrip(b"\n")
        if not entry:
            continue
        if re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", entry):
            commits += 1
            continue
        insertions, deletions, path = entry.split(b"\t", 2)
        paths.add(path)
        if insertions != b"-":
            added += int(insertions)
            removed += int(deletions)
    return commits, len(paths), added, removed


def safe_label(value: str, limit: int) -> str:
    value = re.sub(r"[\x00-\x1f\x7f-\x9f\ud800-\udfff\ufffe\uffff]", " ", value)
    if len(value) > limit:
        value = value[:limit - 1] + "…"
    return escape(value)


MONO = "Consolas, DejaVu Sans Mono, monospace"
STYLES = {
    "classic": (MONO, "#242821", "#52614c", "#216143", "#993c34"),
    "pixel": (MONO, "#c5ffa8", "#95beaa", "#a4ff66", "#ff9c88"),
    "vintage": ("Georgia, serif", "#4d3020", "#77523a", "#44613a", "#8a3427"),
    "grunge": (MONO, "#eae4d8", "#bbb1a0", "#c1db99", "#f5a284"),
    "sticker": ("Trebuchet MS, sans-serif", "#392a54", "#694880", "#23694f", "#9d325e"),
}

BACKGROUNDS = {
    "pixel": """
  <rect width="420" height="430" fill="#112023"/>
  <path d="M30 22H390V30H398V400H390V408H30V400H22V30H30Z" fill="#1a3230" stroke="#8bea7e" stroke-width="4"/>
  <defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 1H4" stroke="#071414" opacity=".25"/></pattern></defs>
  <rect x="30" y="30" width="360" height="370" fill="url(#scan)"/>
  <path d="M351 49h8v-8h8v8h8v8h-8v8h-8v-8h-8Z" fill="#a4ff66"/>
""",
    "vintage": """
  <defs><linearGradient id="paper"><stop stop-color="#d0a370"/><stop offset=".2" stop-color="#f0d5a8"/><stop offset=".8" stop-color="#eccea0"/><stop offset="1" stop-color="#c89660"/></linearGradient></defs>
  <rect width="420" height="430" rx="18" fill="#654332"/>
  <path d="M20 31l52-11 42 5 82-7 74 8 82-6 47 12-7 67 5 91-5 111 7 92-50 10-47-5-63 10-80-7-48 5-73-8-18-19 6-80-6-86 5-97Z" fill="url(#paper)"/>
  <rect x="35" y="36" width="350" height="354" rx="8" fill="none" stroke="#855738" stroke-width="2"/>
  <path d="M352 51l7 7-7 7-7-7Z M366 51l7 7-7 7-7-7Z" fill="#855738"/>
""",
    "grunge": """
  <defs><pattern id="grit" width="47" height="31" patternUnits="userSpaceOnUse"><path d="M1 6h4m31 4h2M13 22h6m24 6h3M25 15h2" stroke="#ded8bd" opacity=".13"/><path d="M2 26h9M18 2h7m8 17h10" stroke="#151412" opacity=".45"/></pattern></defs>
  <rect width="420" height="430" rx="16" fill="#1c1b19"/>
  <path d="M19 25l54-9 71 9 67-4 54 8 66-12 70 12-7 71 6 92-6 83 7 117-58-2-66 12-54-6-76 13-52-8-63 4-14-51 5-87-8-73 6-89Z" fill="#37342e"/>
  <rect x="30" y="32" width="360" height="359" fill="url(#grit)"/>
  <path d="M33 183l350-25M40 337l342-11" stroke="#151412" opacity=".27"/>
  <path d="M352 47l20 2-2 15-20-2Z" fill="#b79163" opacity=".75"/>
""",
    "sticker": """
  <rect width="420" height="430" rx="28" fill="#eadcff"/>
  <rect x="24" y="27" width="376" height="388" rx="36" fill="#bd9de4"/>
  <rect x="20" y="20" width="376" height="388" rx="36" fill="#fff5fc" stroke="#fff" stroke-width="5"/>
  <path d="M362 66c-4-4-13-9-13-15 0-8 10-9 13-3 3-6 13-5 13 3 0 6-9 11-13 15Z" fill="#ee8db5"/>
  <path d="M340 41v12m-6-6h12m36 12v10m-5-5h10" stroke="#a680da" stroke-width="2" stroke-linecap="round"/>
""",
}


def render(name: str, since: str, stats: tuple[int, int, int, int], style: str = "classic") -> str:
    commits, files, added, removed = stats
    font, ink, muted, green, red = STYLES[style]
    rows = [
        ("COMMITS", f"{commits:,}", ink),
        ("FILES TOUCHED", f"{files:,}", ink),
        ("LINES ADDED", f"+{added:,}", green),
        ("LINES REMOVED", f"−{removed:,}", red),
    ]
    row_markup = []
    for index, (label, value, color) in enumerate(rows):
        y = 204 + index * 32
        row_markup.append(
            f'    <text x="46" y="{y}">{label}</text>\n'
            f'    <text x="374" y="{y}" text-anchor="end" fill="{color}" '
            f'font-weight="bold">{value}</text>'
        )
    rows_svg = "\n".join(row_markup)
    teeth = " ".join(f"l-8 8 l-8 -8" for _ in range(24))
    classic = f"""
  <rect width="420" height="430" rx="22" fill="#e0e6d8"/>
  <path d="M18 16H402V401 {teeth} Z" fill="#fffdf4"/>
"""
    background = BACKGROUNDS.get(style, classic)
    title_size = 33 if style == "vintage" else 36
    title_spacing = ' letter-spacing="2"' if style == "pixel" else ""
    barcode = "".join(
        f'<rect x="{46 + i * 5}" y="353" width="{width}" height="24"/>'
        for i, width in enumerate([2, 4, 1, 3, 2, 1, 4, 3, 1, 2, 4, 1, 3, 2, 4, 1])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="430" viewBox="0 0 420 430" role="img" aria-labelledby="title desc">
  <title id="title">Git receipt for {safe_label(name, 60)}</title>
  <desc id="desc">{commits} commits, {files} files touched, {added} lines added, {removed} lines removed.</desc>
{background.rstrip()}
  <g font-family="{font}" fill="{ink}">
    <text x="46" y="60" font-size="12" fill="{muted}">LOCAL GIT HISTORY</text>
    <text x="44" y="101" font-weight="bold" font-size="{title_size}"{title_spacing}>COMMIT RECEIPT</text>
    <text x="46" y="134" font-size="17" font-weight="bold">{safe_label(name, 28)}</text>
    <text x="46" y="155" font-size="12" fill="{muted}">SINCE {safe_label(since, 35)}</text>
    <path d="M46 174H374 M46 327H374" stroke="{muted}" stroke-dasharray="4 5" opacity=".7"/>
    <g font-size="15">
{rows_svg}
    </g>
    <g aria-hidden="true">{barcode}</g>
    <text x="374" y="371" text-anchor="end" font-size="12">THANKS FOR COMMITTING</text>
  </g>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", type=Path, default=Path("."), help="path to a Git repository")
    parser.add_argument("--since", default="7 days ago", help="start date as understood by Git")
    parser.add_argument("--style", choices=STYLES, default="classic", help="receipt style (default: classic)")
    parser.add_argument("-o", "--output", type=Path, default=Path("receipt.svg"), help="output SVG path")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        stats = read_history(repo, args.since)
        svg = render(repo.name or str(repo), args.since, stats, args.style)
        args.output.write_text(svg, encoding="utf-8")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        print(f"git-receipt: {detail or 'Git could not read HEAD.'}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"git-receipt: {error}", file=sys.stderr)
        return 1
    print(f"Saved {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
