"""ScoreStatsCollector: per-game aggregates over per-player total scores.

For each finished game, records:
  - sum, avg (mean), max of per-player total scores,
  - percentiles p95 / p90 / p80 / p60 / p20 / p5 (numpy.percentile,
    linear interpolation).

Plus per-row metadata read from the caller-supplied context:
  - `i`, `j`         -- grid coordinates (any hashables, but typically ints);
  - `n_defect`, `p`  -- semantic labels for the caller's sweep axes.

The `context` dict passed to `collect(...)` must contain those four keys.

Designed to be usable with both `Multigame.run()` and
`Multigame.run_parallel(...)`. Defines `merge(other)` for the parallel
case; the no-arg constructor is also required by `run_parallel`.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np

from pd.collector import Collector
from pd.game import Game


PERCENTILES: tuple[int, ...] = (95, 90, 80, 60, 20, 5)
METRICS: tuple[str, ...] = ("sum", "avg", "max") + tuple(f"p{q}" for q in PERCENTILES)


@dataclass
class GameStats:
    """One row per finished game."""

    i: int
    j: int
    n_defect: int
    p: float
    metrics: dict[str, float]


class ScoreStatsCollector(Collector):
    """Collect per-game score aggregates for a 2D sweep."""

    def __init__(self) -> None:
        self.rows: list[GameStats] = []

    def collect(self, game: Game, context: dict) -> None:
        scores = [p.total_score() for p in game.players]

        metrics: dict[str, float] = {
            "sum": float(sum(scores)),
            "avg": statistics.fmean(scores),
            "max": float(max(scores)),
        }
        pct_values = np.percentile(scores, PERCENTILES)
        for q, v in zip(PERCENTILES, pct_values):
            metrics[f"p{q}"] = float(v)

        self.rows.append(
            GameStats(
                i=context["i"],
                j=context["j"],
                n_defect=context["n_defect"],
                p=context["p"],
                metrics=metrics,
            )
        )

    def merge(self, other: Collector) -> None:  # type: ignore[override]
        if not isinstance(other, ScoreStatsCollector):
            raise TypeError(
                f"ScoreStatsCollector can only merge with itself; got {type(other).__name__}"
            )
        self.rows.extend(other.rows)
