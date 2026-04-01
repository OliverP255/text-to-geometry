#!/usr/bin/env python3
"""
Build comparison figures from benchmark_aggregate.json (run aggregate_benchmark_ratings.py first).

Outputs (PNG) under agent/experiments/figures/:
  - benchmark_models_fidelity_and_validation.png — horizontal bars: mean fidelity (1–5) vs validator pass %
  - benchmark_band_heatmap.png — models × band mean fidelity
  - benchmark_band_spaghetti.png — each model’s profile across B1–B5
  - benchmark_band_aggregate.png — per band: mean ± stdev across models (+ min/max whiskers)
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent
_AGG = _ROOT / "benchmark_aggregate.json"
_OUT = _ROOT / "figures"

_BAND_ORDER = (
    "band1_steps_dims_1to10",
    "band2_dims_no_steps_11to20",
    "band3_no_dims_21to30",
    "band4_vague_31to40",
    "band5_organic_41to46",
)
_BAND_SHORT = (
    "B1: steps + dims\n(1–10)",
    "B2: dims\n(11–20)",
    "B3: no dims\n(21–30)",
    "B4: vague\n(31–40)",
    "B5: organic\n(41–46)",
)


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
            "ytick.labelsize": 8,
            "legend.frameon": False,
            "legend.fontsize": 8,
        }
    )


def _load_rows() -> list[dict]:
    if not _AGG.is_file():
        print(f"Missing {_AGG} — run: python3 {_ROOT / 'aggregate_benchmark_ratings.py'}", file=sys.stderr)
        sys.exit(1)
    rows = json.loads(_AGG.read_text(encoding="utf-8"))
    if not rows:
        print("benchmark_aggregate.json is empty.", file=sys.stderr)
        sys.exit(1)
    return rows


def _sort_by_fidelity(rows: list[dict]) -> list[dict]:
    def key(r: dict) -> tuple[float, str]:
        fm = r.get("fidelity_mean")
        return (-(fm if fm is not None else -1.0), r.get("slug", ""))

    return sorted(rows, key=key)


def plot_models_fidelity_and_validation(rows: list[dict], palette: dict[str, str]) -> None:
    rows = _sort_by_fidelity(rows)
    labels = [r.get("label", r["slug"]) for r in rows]
    fid = [float(r["fidelity_mean"]) if r.get("fidelity_mean") is not None else float("nan") for r in rows]
    val = [float(r["validation_pass_rate"]) for r in rows]

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11.5, 5.2), constrained_layout=True)
    y = np.arange(len(labels))
    h = 0.72

    ax0.barh(y, fid, height=h, color=palette["fidelity"], edgecolor="#1a1a1a", linewidth=0.4)
    ax0.set_xlim(0, 5.0)
    ax0.set_xlabel("Mean prompt fidelity (1–5)")
    ax0.set_title("Model comparison — prompt fidelity")
    ax0.set_yticks(y)
    ax0.set_yticklabels(labels)
    ax0.invert_yaxis()
    for i, v in enumerate(fid):
        if not np.isnan(v):
            ax0.text(min(v + 0.08, 4.85), i, f"{v:.2f}", va="center", fontsize=8, color="#333")

    ax1.barh(y, val, height=h, color=palette["validation"], edgecolor="#1a1a1a", linewidth=0.4)
    ax1.set_xlim(0, 105)
    ax1.set_xlabel("WGSL validator pass rate (%)")
    ax1.set_title("Model comparison — syntactic validation")
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    for i, v in enumerate(val):
        ax1.text(min(v + 1.5, 98), i, f"{v:.1f}%", va="center", fontsize=8, color="#333")

    fig.suptitle("Nine LLMs on 46 CAD / organic prompts", fontsize=14, fontweight="600", y=1.02)
    fig.savefig(_OUT / "benchmark_models_fidelity_and_validation.png", bbox_inches="tight")


def plot_band_heatmap(rows: list[dict], cmap_name: str = "YlOrRd") -> None:
    rows = _sort_by_fidelity(rows)
    mat: list[list[float]] = []
    ylabels: list[str] = []
    for r in rows:
        ylabels.append(r.get("label", r["slug"]))
        bands = r.get("fidelity_bands") or {}
        row = []
        for k in _BAND_ORDER:
            v = bands.get(k)
            row.append(float(v) if v is not None else float("nan"))
        mat.append(row)
    arr = np.array(mat, dtype=np.float64)

    fig, ax = plt.subplots(figsize=(9.2, 6.0), constrained_layout=True)
    im = ax.imshow(arr, aspect="auto", cmap=cmap_name, vmin=1.0, vmax=5.0)
    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label("Mean band fidelity (1–5)")

    ax.set_xticks(np.arange(len(_BAND_ORDER)))
    ax.set_xticklabels(_BAND_SHORT, fontsize=8)
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_title("Fidelity by prompt band (rows = models, sorted by overall mean)")

    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            val = arr[i, j]
            if np.isnan(val):
                t = "—"
                tc = "#666"
            else:
                t = f"{val:.2f}"
                tc = "#faf9f7" if val > 3.4 else "#1a1a1a"
            ax.text(j, i, t, ha="center", va="center", fontsize=7.5, color=tc)

    fig.savefig(_OUT / "benchmark_band_heatmap.png", bbox_inches="tight")


def plot_band_spaghetti(rows: list[dict]) -> None:
    rows_sorted = _sort_by_fidelity(rows)
    colors = plt.cm.tab10(np.linspace(0, 0.9, len(rows_sorted)))
    x = np.arange(len(_BAND_ORDER))

    fig, ax = plt.subplots(figsize=(10, 5.8), constrained_layout=True)
    for i, r in enumerate(rows_sorted):
        bands = r.get("fidelity_bands") or {}
        ys = [float(bands.get(k)) if bands.get(k) is not None else float("nan") for k in _BAND_ORDER]
        ax.plot(x, ys, "o-", color=colors[i], linewidth=1.8, markersize=5, label=r.get("label", r["slug"]))

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("\n", " ") for s in _BAND_SHORT], fontsize=8)
    ax.set_ylabel("Mean fidelity (1–5)")
    ax.set_ylim(0.5, 5.35)
    ax.set_title("Band profiles: how each model shifts across prompt types")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    fig.savefig(_OUT / "benchmark_band_spaghetti.png", bbox_inches="tight")


def plot_band_aggregate(rows: list[dict], palette: dict[str, str]) -> None:
    """Per band: mean and stdev of band-mean across models; show min/max as caps."""
    series: list[list[float]] = [[] for _ in _BAND_ORDER]
    for r in rows:
        bands = r.get("fidelity_bands") or {}
        for j, k in enumerate(_BAND_ORDER):
            v = bands.get(k)
            if v is not None:
                series[j].append(float(v))

    means = [statistics.mean(s) if s else float("nan") for s in series]
    stds = [statistics.stdev(s) if len(s) > 1 else 0.0 for s in series]
    mins = [min(s) if s else float("nan") for s in series]
    maxs = [max(s) if s else float("nan") for s in series]

    x = np.arange(len(_BAND_ORDER))
    fig, ax = plt.subplots(figsize=(9.5, 5.2), constrained_layout=True)
    w = 0.62
    ax.bar(
        x,
        means,
        width=w,
        color=palette["aggregate"],
        edgecolor="#1a1a1a",
        linewidth=0.5,
        yerr=stds,
        capsize=4,
        error_kw={"linewidth": 1.2, "ecolor": "#333"},
    )

    for i, (lo, hi, m) in enumerate(zip(mins, maxs, means)):
        if np.isnan(m):
            continue
        ax.plot([i, i], [lo, hi], color="#555", linewidth=1.0, linestyle="--", zorder=0)
        ax.plot(i, lo, marker="_", color="#555", markersize=10, markeredgewidth=1.2)
        ax.plot(i, hi, marker="_", color="#555", markersize=10, markeredgewidth=1.2)

    ax.set_xticks(x)
    ax.set_xticklabels(_BAND_SHORT, fontsize=8)
    ax.set_ylabel("Fidelity (1–5)")
    ax.set_ylim(0, 5.4)
    ax.set_title("Across all models: average band difficulty ± spread")
    ax.text(
        0.02,
        0.02,
        "Bar = mean of 9 model band-means; error bars = stdev;\ndashed = min–max across models.",
        transform=ax.transAxes,
        fontsize=8,
        color="#444",
        va="bottom",
    )
    fig.savefig(_OUT / "benchmark_band_aggregate.png", bbox_inches="tight")


def main() -> None:
    _setup_style()
    _OUT.mkdir(parents=True, exist_ok=True)
    rows = _load_rows()
    rows = [r for r in rows if "error" not in r]

    palette = {
        "fidelity": "#2d6a4f",
        "validation": "#1c3d5a",
        "aggregate": "#bc6c25",
    }

    plot_models_fidelity_and_validation(rows, palette)
    plot_band_heatmap(rows)
    plot_band_spaghetti(rows)
    plot_band_aggregate(rows, palette)

    print(f"Wrote figures to {_OUT}:")
    for name in (
        "benchmark_models_fidelity_and_validation.png",
        "benchmark_band_heatmap.png",
        "benchmark_band_spaghetti.png",
        "benchmark_band_aggregate.png",
    ):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
