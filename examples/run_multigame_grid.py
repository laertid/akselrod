"""Multigame demo: sweep a couple of strategy line-ups across seeds.

Two rows of the grid correspond to two match-ups; the columns are
independent seeds. A minimal Collector accumulates one row per game.
"""

from __future__ import annotations

import random

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Collector,
    Game,
    Multigame,
    TitForTat,
)


class RowCollector(Collector):
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def collect(self, game, context):
        self.rows.append(
            {
                **context,
                "scores": game.scores(),
                "deals": len(game.history),
            }
        )


def make_game(strategies, rounds, seed):
    return Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=[cls() for cls in strategies],
        total_rounds=rounds,
        rng=random.Random(seed),
    )


def main() -> None:
    seeds = [1, 2, 3]

    grid = [
        [
            (
                make_game([TitForTat, AlwaysDefect], rounds=100, seed=s),
                {"lineup": "TFT vs AllD", "seed": s},
            )
            for s in seeds
        ],
        [
            (
                make_game([TitForTat, AlwaysCooperate], rounds=100, seed=s),
                {"lineup": "TFT vs AllC", "seed": s},
            )
            for s in seeds
        ],
    ]

    collector = RowCollector()
    Multigame(grid, collector).run()

    print(f"{len(collector.rows)} games played")
    for row in collector.rows:
        print(
            f"  {row['lineup']:<15} seed={row['seed']}  "
            f"scores={row['scores']}  deals={row['deals']}"
        )


if __name__ == "__main__":
    main()
