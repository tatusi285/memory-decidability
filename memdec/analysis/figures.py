"""Figure generation, dependency-free.

The study's figures were drawn with Pillow inside the measurement script, which meant
a figure could only be reproduced by re-running an experiment.  Here the figures are
plain SVG assembled from the shipped result files: text, diffable, and renderable in
any browser with no plotting library installed.

Two figures reproduce the paper and one is new:

``figure1_delay_curves.svg``
    Stale rate by update delay for the four presentation conditions.
``figure2_filler_curve.svg``
    Stale rate as neutral filler sentences are added, with exact intervals.
``figure3_conflict_selectivity.svg``
    Archive coverage per policy against the uniform-random reference, which is the
    comparison the paper's Table 4 does not make.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import manifest
from ..policies import POLICIES, POLICY_INFO, random_selection_hit_rate
from . import tables

FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
PALETTE = {
    "date": "#1f6feb",
    "day": "#d29922",
    "none_newest": "#cf222e",
    "none_oldest": "#1a7f37",
    "tail": "#cf222e",
    "gap": "#1f6feb",
    "reference": "#6e7781",
}


@dataclass(frozen=True)
class Point:
    label: str
    value: float
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True)
class Series:
    name: str
    points: tuple[Point, ...]
    color: str
    dashed: bool = False


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _frame(width: int, height: int, margin: tuple[int, int, int, int],
           title: str, xlabel: str, ylabel: str,
           y_ticks: list[float], y_max: float) -> tuple[list[str], float, float, float, float]:
    left, right, top, bottom = margin
    plot_w = width - left - right
    plot_h = height - top - bottom
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{left}" y="32" font-family="{FONT}" font-size="19" font-weight="600" '
        f'fill="#1f2328">{_esc(title)}</text>',
        f'<text x="{left}" y="{top - 14}" font-family="{FONT}" font-size="12" '
        f'fill="#57606a">{_esc(ylabel)}</text>',
    ]
    for tick in y_ticks:
        y = top + plot_h - plot_h * (tick / y_max)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" '
            f'stroke="#eaeef2" stroke-width="1"/>')
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-family="{FONT}" font-size="12" fill="#57606a">{tick:g}%</text>')
    parts.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" '
        f'stroke="#8c959f" stroke-width="1.2"/>')
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" '
        f'stroke="#8c959f" stroke-width="1.2"/>')
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 12}" text-anchor="middle" '
        f'font-family="{FONT}" font-size="12" fill="#57606a">{_esc(xlabel)}</text>')
    return parts, left, top, plot_w, plot_h


def line_chart(title: str, xlabel: str, ylabel: str, x_labels: list[str],
               series: list[Series], *, width: int = 940, height: int = 540,
               y_max: float = 100.0, y_ticks: list[float] | None = None) -> str:
    """Categorical line chart with optional 95% error bars.

    The canvas widens to fit the longest legend entry, because a clipped label is
    the one failure mode a rendered figure cannot recover from.
    """
    label_px = max(len(s.name) for s in series) * 6.7 + 40
    margin = (86, int(46 + label_px), 96, 62)
    left, right, top, bottom = margin
    width = max(width, left + 560 + right)
    parts, left, top, plot_w, plot_h = _frame(
        width, height, margin, title, xlabel, ylabel,
        y_ticks if y_ticks is not None else [0, 25, 50, 75, 100], y_max)

    n = len(x_labels)
    step = plot_w / max(1, n - 1) if n > 1 else plot_w
    xs = [left + (step * i if n > 1 else plot_w / 2) for i in range(n)]

    for x, label in zip(xs, x_labels, strict=False):
        parts.append(
            f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" '
            f'y2="{top + plot_h + 6}" stroke="#8c959f"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{top + plot_h + 22}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="12" fill="#57606a">{_esc(label)}</text>')

    def ypos(value: float) -> float:
        return top + plot_h - plot_h * (value / y_max)

    for s in series:
        coords = []
        for i, point in enumerate(s.points):
            coords.append((xs[i], ypos(point.value)))
        dash = ' stroke-dasharray="6 4"' if s.dashed else ""
        parts.append(
            f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in coords)}" '
            f'fill="none" stroke="{s.color}" stroke-width="2.4"{dash} '
            f'stroke-linejoin="round" stroke-linecap="round"/>')
        for (x, y), point in zip(coords, s.points, strict=False):
            if point.low is not None and point.high is not None:
                y_lo, y_hi = ypos(point.high), ypos(point.low)
                parts.append(
                    f'<line x1="{x:.1f}" y1="{y_lo:.1f}" x2="{x:.1f}" y2="{y_hi:.1f}" '
                    f'stroke="{s.color}" stroke-width="1.3" opacity="0.75"/>')
                for y_cap in (y_lo, y_hi):
                    parts.append(
                        f'<line x1="{x - 4:.1f}" y1="{y_cap:.1f}" x2="{x + 4:.1f}" '
                        f'y2="{y_cap:.1f}" stroke="{s.color}" stroke-width="1.3" '
                        f'opacity="0.75"/>')
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{s.color}" '
                f'stroke="#ffffff" stroke-width="1.2"/>')

    # legend, right side, starting just outside the plot frame
    legend_x = left + plot_w + 14
    legend_y = top + 4
    for index, s in enumerate(series):
        y = legend_y + index * 22
        dash = ' stroke-dasharray="6 4"' if s.dashed else ""
        parts.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 22}" y2="{y}" '
            f'stroke="{s.color}" stroke-width="2.6"{dash}/>')
        parts.append(
            f'<text x="{legend_x + 30}" y="{y + 4}" font-family="{FONT}" font-size="12" '
            f'fill="#1f2328">{_esc(s.name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def bar_chart(title: str, xlabel: str, bars: list[tuple[str, float, str]],
              reference: tuple[str, float] | None = None, *, width: int = 860,
              height: int = 430) -> str:
    """Horizontal bar chart with the value axis along the bottom.

    Written separately from :func:`line_chart` because a horizontal bar chart needs a
    horizontal value axis; reusing the vertical frame put the tick labels on the wrong
    side of the bars.
    """
    label_px = max(len(name) for name, _, _ in bars) * 7.2
    left = int(max(120, label_px + 26))
    right, top, bottom = 76, 92, 76
    plot_w = width - left - right
    plot_h = height - top - bottom
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{_esc(title)}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="34" font-family="{FONT}" font-size="18" font-weight="600" '
        f'fill="#1f2328">{_esc(title)}</text>',
    ]

    def xpos(value: float) -> float:
        return left + plot_w * (min(100.0, max(0.0, value)) / 100.0)

    for tick in (0, 25, 50, 75, 100):
        x = xpos(tick)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" '
                     f'stroke="#eaeef2" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 20}" text-anchor="middle" '
                     f'font-family="{FONT}" font-size="12" fill="#57606a">{tick}%</text>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" '
                 f'y2="{top + plot_h}" stroke="#8c959f" stroke-width="1.2"/>')
    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 18}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="12" fill="#57606a">{_esc(xlabel)}</text>')

    slot = plot_h / len(bars)
    bar_h = min(38.0, slot * 0.52)
    for index, (name, value, color) in enumerate(bars):
        y = top + slot * index + (slot - bar_h) / 2
        x_end = xpos(value)
        parts.append(f'<rect x="{left}" y="{y:.1f}" width="{max(1.5, x_end - left):.1f}" '
                     f'height="{bar_h:.1f}" fill="{color}" rx="3"/>')
        parts.append(f'<text x="{left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
                     f'font-family="{FONT}" font-size="13" fill="#1f2328">{_esc(name)}</text>')
        parts.append(f'<text x="{x_end + 8:.1f}" y="{y + bar_h * 0.72:.1f}" '
                     f'font-family="{FONT}" font-size="12.5" fill="#1f2328">'
                     f'{value:.1f}%</text>')

    if reference is not None:
        name, value = reference
        x = xpos(value)
        parts.append(f'<line x1="{x:.1f}" y1="{top - 16}" x2="{x:.1f}" '
                     f'y2="{top + plot_h}" stroke="#6e7781" stroke-width="1.6" '
                     f'stroke-dasharray="5 4"/>')
        anchor, offset = ("start", 8) if x < left + plot_w * 0.72 else ("end", -8)
        parts.append(f'<text x="{x + offset:.1f}" y="{top - 24}" text-anchor="{anchor}" '
                     f'font-family="{FONT}" font-size="12" fill="#57606a">{_esc(name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# The three figures
# --------------------------------------------------------------------------- #
FIGURE1_CONDITIONS = (
    ("Absolute dates, newest first", "out_live_date", PALETTE["date"], False),
    ("Relative notation (day N)", "out_live", PALETTE["day"], False),
    ("No timestamp, newest first", "out_live_bare", PALETTE["none_newest"], False),
    ("No timestamp, oldest first", "out_live_bare_rev", PALETTE["none_oldest"], False),
)


def figure1() -> str:
    delays = [1, 7, 30, 90]
    series = []
    for label, run_id, color, dashed in FIGURE1_CONDITIONS:
        points = []
        for delay in delays:
            c = tables.cell(run_id, "none", delay)
            points.append(Point(str(delay), c.mean * 100, c.lo * 100, c.hi * 100))
        series.append(Series(label, tuple(points), color, dashed))
    return line_chart(
        "Stale rate by update delay, deepseek-chat, no review",
        "Update delay (days before the query)",
        "Stale rate (%, lower is better)",
        [str(d) for d in delays], series)


def figure2() -> str:
    points_tail = []
    for k in (0, 1, 2, 4, 8, 16):
        c = tables.cell(f"out_fill2_tail_{k}", "none")
        points_tail.append(Point(str(k), c.mean * 100, c.lo * 100, c.hi * 100))
    gap = [tables.cell(f"out_fill2_gap_{k}", "none") for k in (1, 8)]
    return line_chart(
        "Neutral filler sentences: after both records vs between them",
        "Filler sentences appended (k)",
        "Stale rate (%)",
        ["0", "1", "2", "4", "8", "16"],
        [Series("Appended after both records", tuple(points_tail), PALETTE["tail"]),
         Series("Inserted between records (k = 1, 8 only)",
                tuple(Point(str(k), c.mean * 100, c.lo * 100, c.hi * 100)
                      for k, c in zip((1, 8), gap, strict=False)), PALETTE["gap"], True)],
    )


def figure3() -> str:
    spec = manifest.load_runs()["out_live_bare"]
    bars = []
    colors = {"none": "#8c959f", "recent": "#cf222e",
              "importance": "#1f6feb", "decay": "#1a7f37"}
    for policy in POLICIES:
        coverage = (manifest.count_mean("out_live_bare", policy, "archived") or 0.0) / spec.chains
        bars.append((POLICY_INFO[policy]["name_en"], coverage * 100, colors[policy]))
    reference = ("uniform random selection",
                 random_selection_hit_rate(spec.chains) * 100)
    return bar_chart(
        "Archive coverage by review policy vs a random-selection baseline",
        "Share of the 40 conflicting pairs archived", bars, reference)


def all_figures() -> dict[str, str]:
    return {
        "figure1_delay_curves.svg": figure1(),
        "figure2_filler_curve.svg": figure2(),
        "figure3_conflict_selectivity.svg": figure3(),
    }


def write_figures(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, svg in all_figures().items():
        path = directory / name
        # Explicit LF so a Windows checkout matches the committed blob exactly.
        path.write_text(svg, encoding="utf-8", newline="\n")
        written.append(path)
    return written
