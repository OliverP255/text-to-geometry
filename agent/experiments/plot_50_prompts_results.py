#!/usr/bin/env python3
"""Build publication-style figures from data/50_prompts_scores.json."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parent
_DATA = _ROOT / "data" / "50_prompts_scores.json"
_OUT = _ROOT / "figures"

# Aligned with agent/experiments/test_50_prompts.py (PROMPTS order, 46 prompts).
CATEGORY_DEFS: list[tuple[str, tuple[int, int]]] = [
    ("Classic CAD (dims + steps)", (1, 10)),
    ("Classic CAD (dims, no steps)", (11, 20)),
    ("Classic CAD (no dims, no steps)", (21, 30)),
    ("Classic CAD (vague)", (31, 40)),
    ("Organic (SDF)", (41, 46)),
]


def _category_for_prompt_index(n: int) -> str:
    for name, (lo, hi) in CATEGORY_DEFS:
        if lo <= n <= hi:
            return name
    raise ValueError(f"Prompt index {n} not in any category")


def _scores_by_category(rows: list[dict]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {name: [] for name, _ in CATEGORY_DEFS}
    for r in rows:
        try:
            cat = _category_for_prompt_index(int(r["n"]))
        except ValueError:
            continue
        out[cat].append(int(r["score"]))
    return out


def _stdev(xs: list[int]) -> float:
    return statistics.stdev(xs) if len(xs) > 1 else 0.0


def _tier_counts(scores: list[int]) -> tuple[int, int, int, int]:
    """Excellent ≥90, Good 70–89, Fair 50–69, Poor <50."""
    ex = sum(1 for s in scores if s >= 90)
    gd = sum(1 for s in scores if 70 <= s < 90)
    fr = sum(1 for s in scores if 50 <= s < 70)
    pr = sum(1 for s in scores if s < 50)
    return ex, gd, fr, pr


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 220,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
            "axes.facecolor": "#f7f5f2",
            "figure.facecolor": "#faf9f7",
            "axes.edgecolor": "#2a2a2a",
            "axes.labelcolor": "#1a1a1a",
            "text.color": "#1a1a1a",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "grid.color": "#d8d4cc",
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.titlesize": 13,
            "axes.titleweight": "600",
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
        }
    )


def main() -> None:
    _setup_style()
    _OUT.mkdir(parents=True, exist_ok=True)

    rows = json.loads(_DATA.read_text(encoding="utf-8"))
    n_total = len(rows)
    ns = [r["n"] for r in rows]
    scores = [r["score"] for r in rows]
    n_max = max(ns) if ns else 1
    mean = statistics.mean(scores)
    med = statistics.median(scores)
    stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0

    # --- Palette (editorial: ink + terracotta + sage + slate)
    c_line = "#1c3d5a"
    c_fill = "#3d6b8a"
    c_hist = "#8b6914"
    c_tiers = ["#2d6a4f", "#40916c", "#d4a373", "#9d0208"]

    # 1) Scores along prompt index
    fig, ax = plt.subplots(figsize=(12.5, 4.2), layout="constrained")
    ax.fill_between(ns, scores, alpha=0.12, color=c_fill, linewidth=0)
    ax.plot(ns, scores, color=c_line, linewidth=1.35, marker="o", markersize=3.8, markerfacecolor=c_line, markeredgewidth=0)
    ax.axhline(mean, color="#6c757d", linestyle="--", linewidth=1.0, label=f"Mean ({mean:.1f})")
    ax.axhline(med, color="#adb5bd", linestyle=":", linewidth=1.0, label=f"Median ({med:.0f})")
    ax.set_xlabel("Prompt index")
    ax.set_ylabel("Semantic score (0–100)")
    ax.set_title("WGSL output vs prompt — score by case")
    ax.set_xlim(0.5, float(n_max) + 0.5)
    ax.set_ylim(-2, 105)
    ax.legend(loc="upper right", fontsize=9)
    fig.savefig(_OUT / "scores_by_prompt_index.png")
    plt.close(fig)

    # 2) Histogram
    fig, ax = plt.subplots(figsize=(8.2, 4.4), layout="constrained")
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 101]
    n_hist, edges, patches = ax.hist(scores, bins=bins, edgecolor="#2a2a2a", linewidth=0.45)
    # Gradient-ish fill by bin center
    cmap = plt.colormaps["YlOrBr"]
    for i, p in enumerate(patches):
        p.set_facecolor(cmap(0.25 + 0.65 * (i / max(len(patches) - 1, 1))))
    ax.axvline(mean, color=c_line, linestyle="--", linewidth=1.2, label=f"Mean = {mean:.1f}")
    ax.set_xlabel("Score")
    ax.set_ylabel("Number of prompts")
    ax.set_title("Distribution of semantic scores")
    ax.legend(loc="upper right", fontsize=9)
    fig.savefig(_OUT / "scores_histogram.png")
    plt.close(fig)

    # 3) Tier horizontal bar
    tiers = [
        ("Excellent (90–100)", sum(1 for s in scores if s >= 90)),
        ("Good (70–89)", sum(1 for s in scores if 70 <= s < 90)),
        ("Fair (50–69)", sum(1 for s in scores if 50 <= s < 70)),
        ("Poor (<50)", sum(1 for s in scores if s < 50)),
    ]
    labels = [t[0] for t in tiers]
    counts = [t[1] for t in tiers]
    y = range(len(labels))
    fig, ax = plt.subplots(figsize=(8.0, 3.2), layout="constrained")
    bars = ax.barh(labels, counts, color=c_tiers, height=0.62, edgecolor="#1a1a1a", linewidth=0.5)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + 0.35, bar.get_y() + bar.get_height() / 2, str(int(c)), va="center", fontsize=10, color="#1a1a1a")
    ax.set_xlabel(f"Count (of {n_total} prompts)")
    ax.set_title("Prompts by score band")
    ax.set_xlim(0, max(counts) + 6)
    fig.savefig(_OUT / "scores_by_tier.png")
    plt.close(fig)

    # 4) Compact summary strip (sparkline + stats box)
    fig, ax = plt.subplots(figsize=(10, 2.2), layout="constrained")
    ax.plot(ns, scores, color=c_line, linewidth=1.4)
    ax.fill_between(ns, scores, alpha=0.15, color=c_fill)
    ax.set_xlim(0.5, float(n_max) + 0.5)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Prompt #")
    ax.set_ylabel("Score")
    ax.set_title(f"{n_total}-prompt run — overview")
    stats_txt = f"Mean {mean:.1f}   ·   Median {med:.0f}   ·   σ {stdev:.1f}   ·   min {min(scores)}   ·   max {max(scores)}"
    ax.text(0.5, -0.28, stats_txt, transform=ax.transAxes, ha="center", fontsize=10, color="#444444")
    fig.savefig(_OUT / "scores_overview_strip.png")
    plt.close(fig)

    # --- Category aggregates (only categories with ≥1 scored prompt)
    by_cat = _scores_by_category(rows)
    cat_names = [name for name, _ in CATEGORY_DEFS if by_cat[name]]
    cat_means = [statistics.mean(by_cat[c]) for c in cat_names]
    cat_stdev = [_stdev(by_cat[c]) for c in cat_names]
    cat_ns = [len(by_cat[c]) for c in cat_names]

    c_cat = ["#1c3d5a", "#5c4d7d", "#2f6f5e", "#8b5a2b", "#7c5cbf"]
    name_to_ci = {name: i for i, (name, _) in enumerate(CATEGORY_DEFS)}
    bar_colors = [c_cat[name_to_ci[c] % len(c_cat)] for c in cat_names]

    # 5) Mean score by category (+ sample stdev as error bars)
    fig, ax = plt.subplots(figsize=(11.0, 5.0), layout="constrained")
    x = range(len(cat_names))
    ax.bar(
        x,
        cat_means,
        yerr=cat_stdev,
        capsize=5,
        color=bar_colors,
        edgecolor="#1a1a1a",
        linewidth=0.6,
        error_kw={"elinewidth": 1.0, "capthick": 1.0, "ecolor": "#333333"},
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(cat_names, rotation=22, ha="right")
    ax.set_ylabel("Mean semantic score (0–100)")
    ax.set_ylim(0, 105)
    ax.set_title("Mean score by prompt category (bars ± within-category stdev)")
    for i, (m, n_s, sd) in enumerate(zip(cat_means, cat_ns, cat_stdev)):
        ax.text(
            i,
            min(m + sd + 4, 102),
            f"n={n_s}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#444444",
        )
    fig.savefig(_OUT / "scores_mean_by_category.png")
    plt.close(fig)

    # 6) Quality mix by category — stacked horizontal bars
    tier_labels = ["Excellent\n(≥90)", "Good\n(70–89)", "Fair\n(50–69)", "Poor\n(<50)"]
    tier_colors = c_tiers
    ex_c, gd_c, fr_c, pr_c = zip(*(_tier_counts(by_cat[c]) for c in cat_names))
    ex_c, gd_c, fr_c, pr_c = list(ex_c), list(gd_c), list(fr_c), list(pr_c)

    fig, ax = plt.subplots(figsize=(10.0, 5.2), layout="constrained")
    y = range(len(cat_names))
    left = [0.0] * len(cat_names)

    def _stack_row(counts: list[int], color: str, label: str) -> None:
        nonlocal left
        ax.barh(
            y,
            counts,
            left=left,
            height=0.68,
            color=color,
            edgecolor="#1a1a1a",
            linewidth=0.45,
            label=label,
        )
        left = [left[i] + counts[i] for i in range(len(cat_names))]

    _stack_row(list(pr_c), tier_colors[3], tier_labels[3])
    _stack_row(list(fr_c), tier_colors[2], tier_labels[2])
    _stack_row(list(gd_c), tier_colors[1], tier_labels[1])
    _stack_row(list(ex_c), tier_colors[0], tier_labels[0])

    ax.set_yticks(list(y))
    ax.set_yticklabels(cat_names)
    ax.set_xlabel("Number of prompts")
    ax.set_xlim(0, max(cat_ns) + 0.5)
    ax.set_title("Quality mix by category (stacked counts)")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    fig.savefig(_OUT / "scores_quality_mix_by_category.png")
    plt.close(fig)

    print(f"Wrote figures to {_OUT} (mean={mean:.2f}, median={med:.0f})")


if __name__ == "__main__":
    main()
