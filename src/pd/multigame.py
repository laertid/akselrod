"""Multigame: run a 2D grid of pre-built games and feed each one to a Collector.

The grid is a `list[list[tuple[Game, dict]]]`. Each cell holds:
  - a fully constructed `Game` (its own players, deal generator, rng --
    Multigame does NOT touch RNG or players),
  - a `context` dict that the caller has already populated with whatever
    metadata the Collector will need (coordinates, labels, seeds, ...).

`Multigame.run()` iterates the grid row-major, plays each game exactly
once, and calls `collector.collect(game, context)` immediately after the
game finishes. Games are played sequentially -- the 2D shape is only a
grouping convention for the caller / Collector, it does not imply any
parallelism or between-row dependency.

Results live inside the Collector; `Multigame.run()` returns nothing.
"""

from __future__ import annotations

from pd.collector import Collector
from pd.game import Game


class Multigame:
    """Sequentially play a 2D grid of games and forward each to a Collector."""

    def __init__(
        self,
        games: list[list[tuple[Game, dict]]],
        collector: Collector,
    ) -> None:
        # Shallow-copy the outer / inner lists so later mutations to the
        # caller's list don't change what we run, but keep the (game,
        # context) tuples themselves shared (Games are heavy, contexts
        # may be intentionally shared references).
        self.games: list[list[tuple[Game, dict]]] = [list(row) for row in games]
        self.collector = collector

    def run(self) -> None:
        """Play every game in row-major order and collect after each one.

        Each Game is played exactly once. Any exception in `game.play()`
        or `collector.collect(...)` propagates immediately and aborts the
        remaining grid; already-collected results stay in the Collector.
        """
        for row in self.games:
            for game, context in row:
                game.play()
                self.collector.collect(game, context)
