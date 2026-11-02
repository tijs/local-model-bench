"""Balanced short/long decode observations and a paired-point figure.

The caller validates terminal run evidence and selects the complete predeclared
cohort. Task wall throughput is not decode TPS. Warmups, interrupted runs and
different runtime/model revisions must never be supplied as measured repeats.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


@dataclass(frozen=True)
class SpeedProfile:
    model: str
    engine: str
    runtime_sha256: str
    model_revision: str
    process_ids: tuple[str, str]
    short_tokens: int
    long_tokens: int


@dataclass(frozen=True)
class SpeedObservation:
    model: str
    process_id: str
    runtime_sha256: str
    model_revision: str
    context: str
    repeat: int
    prompt_tokens: int
    completion_tokens: int
    decode_tps: float


@dataclass(frozen=True)
class ContextSpeedAverage:
    profile: SpeedProfile
    short_tps: float
    long_tps: float
    repeats_per_process: int
    decode_tokens: int
    process_weights: tuple[float, float] = (0.5, 0.5)


def aggregate_context_speeds(
    profiles: list[SpeedProfile],
    observations: list[SpeedObservation],
    *,
    repeats: int = 5,
    decode_tokens: int = 128,
) -> list[ContextSpeedAverage]:
    """Require every declared process/context/repeat; give each process 50%."""
    if not profiles or len({p.model for p in profiles}) != len(profiles):
        raise ValueError("require distinct predeclared model profiles")
    if (
        type(repeats) is not int
        or repeats < 1
        or type(decode_tokens) is not int
        or decode_tokens < 1
    ):
        raise ValueError("require positive repeat and output counts")
    if len({p.long_tokens for p in profiles}) != 1:
        raise ValueError("long-context lengths must match across profiles")
    declared = {}
    for p in profiles:
        if (
            p.engine not in {"mei", "llama.cpp"}
            or not re.fullmatch(r"[0-9a-f]{64}", p.runtime_sha256)
            or not re.fullmatch(r"[0-9a-f]{40}", p.model_revision)
            or len(p.process_ids) != 2
            or len(set(p.process_ids)) != 2
            or any(not identity for identity in p.process_ids)
            or type(p.short_tokens) is not int
            or type(p.long_tokens) is not int
            or not 0 < p.short_tokens < p.long_tokens
        ):
            raise ValueError("invalid pinned profile or independent process identities")
        for process in p.process_ids:
            for context in ("short", "long"):
                for repeat in range(1, repeats + 1):
                    declared[p.model, process, context, repeat] = p
    values = {}
    for row in observations:
        key = row.model, row.process_id, row.context, row.repeat
        p = declared.get(key)
        if p is None or key in values or type(row.repeat) is not int:
            raise ValueError(
                "unexpected or duplicate measured repeat; warmups do not count"
            )
        tokens = p.short_tokens if row.context == "short" else p.long_tokens
        if (
            row.runtime_sha256 != p.runtime_sha256
            or row.model_revision != p.model_revision
            or type(row.prompt_tokens) is not int
            or row.prompt_tokens != tokens
            or type(row.completion_tokens) is not int
            or row.completion_tokens != decode_tokens
            or type(row.decode_tps) not in (float, int)
            or not math.isfinite(row.decode_tps)
            or row.decode_tps <= 0
        ):
            raise ValueError("mismatched runtime/model/count or invalid decode rate")
        values[key] = row.decode_tps
    if values.keys() != declared.keys():
        raise ValueError("missing predeclared measured observations")

    def mean(p: SpeedProfile, context: str) -> float:
        return fmean(
            fmean(values[p.model, process, context, r] for r in range(1, repeats + 1))
            for process in p.process_ids
        )

    return [
        ContextSpeedAverage(
            p, mean(p, "short"), mean(p, "long"), repeats, decode_tokens
        )
        for p in profiles
    ]


def context_speed_figure(
    points: list[ContextSpeedAverage],
    output: Path,
    *,
    title: str,
    provenance: str,
    colors: dict[str, str],
) -> None:
    """Write standalone PNG/SVG; connectors pair endpoints, not interpolation."""
    if not points:
        raise ValueError("cannot draw an empty comparison")
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(10.5, max(4.7, 1.0 * len(points) + 1.7)),
        gridspec_kw={"height_ratios": [1, 0.24]},
        layout="constrained",
    )
    ax, footer = axes
    for y, point in enumerate(points):
        p = point.profile
        color = colors[p.model]
        ax.plot(
            [point.short_tps, point.long_tps],
            [y, y],
            color=color,
            alpha=0.5,
            linewidth=3,
            zorder=1,
        )
        ax.scatter(point.short_tps, y, color=color, s=85, zorder=3)
        ax.scatter(
            point.long_tps,
            y,
            facecolor="white",
            edgecolor=color,
            linewidth=2,
            s=85,
            zorder=3,
        )
        for speed, tokens, offset in (
            (point.short_tps, p.short_tokens, 12),
            (point.long_tps, p.long_tokens, -21),
        ):
            ax.annotate(
                f"{speed:.1f} TPS · {tokens:,} tokens",
                (speed, y),
                xytext=(0, offset),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                color=color,
            )
    ax.set_yticks(
        range(len(points)),
        [
            f"{p.profile.model}  ({'Mei' if p.profile.engine == 'mei' else 'llama.cpp'})"
            for p in points
        ],
    )
    ax.set_ylim(len(points) - 0.45, -0.55)
    ax.set_xlim(0, 1.2 * max(max(p.short_tps, p.long_tps) for p in points))
    ax.set_xlabel("Mean decode tokens per second · higher is better", labelpad=12)
    ax.set_title(title, loc="left", fontweight="bold", pad=20)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.17)
    footer.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                color="#555",
                linestyle="none",
                label="Short context",
            ),
            Line2D(
                [],
                [],
                marker="o",
                color="#555",
                markerfacecolor="white",
                linestyle="none",
                label="Long context",
            ),
        ],
        loc="lower left",
        ncols=2,
        frameon=False,
        fontsize=9,
    )
    footer.axis("off")
    footer.text(
        0,
        1,
        "Each endpoint averages both fresh processes equally. Input token counts shown; cold requests and warmups excluded.\n"
        + provenance,
        fontsize=8,
        color="#555",
        va="top",
        wrap=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output.with_suffix("." + extension), dpi=180, bbox_inches="tight")
    plt.close(fig)
