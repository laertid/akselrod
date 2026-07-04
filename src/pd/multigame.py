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

`Multigame.run_parallel(max_workers=None)` plays the same grid across a
process pool. Each worker plays one game with a fresh
per-worker collector of the same class as `self.collector`, and the
parent merges the worker collectors back into `self.collector` via
`Collector.merge`. Concrete collectors must override `merge` to opt in.

Results live inside the Collector; both `run()` and `run_parallel()`
return nothing.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Type

from pd.collector import Collector
from pd.game import Game


def _run_one_game(
    game: Game,
    context: dict,
    collector_cls: Type[Collector],
) -> Collector:
    """Worker entry point: play one game, collect into a fresh collector.

    Runs inside a worker process. Must be at module scope so it can be
    pickled. Instantiates `collector_cls()` with no arguments -- concrete
    collectors used with `run_parallel` must therefore support this.
    """
    local = collector_cls()
    game.play()
    local.collect(game, context)
    return local


class Multigame:
    """Play a 2D grid of games and forward each to a Collector.

    Two execution modes:

    - `run()`: sequential, row-major, deterministic call order for
      `collector.collect(...)`.
    - `run_parallel(max_workers=None)`: parallel via `ProcessPoolExecutor`.
      Requires the collector class to be picklable, no-arg constructible,
      and to override `Collector.merge`.
    """

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

    def run_parallel(self, max_workers: int | None = None) -> None:
        """Play every game across a process pool and merge the results.

        Each cell in the grid is submitted as an independent task: a
        worker unpickles `(game, context)`, plays the game, collects
        into a fresh instance of `type(self.collector)`, and returns
        that collector back to the parent. The parent then folds each
        worker's collector into `self.collector` via
        `Collector.merge(worker)`.

        Requirements on `self.collector`:
          - Its class must be picklable (import from a real module path,
            not a REPL-defined class).
          - Its class must support `type(self.collector)()` -- i.e.
            take no required constructor arguments.
          - It must override `Collector.merge` to combine two instances;
            the default raises `NotImplementedError`.

        Results ordering: worker collectors are merged in the order tasks
        complete, not row-major. If the caller cares about ordering, it
        must be reconstructed from data the collector already stores
        (e.g. `i` / `j` in each row's context).

        Any exception from a worker propagates on merge; already-merged
        results stay in `self.collector`.
        """
        cells = [cell for row in self.games for cell in row]
        if not cells:
            return
        collector_cls = type(self.collector)
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(_run_one_game, game, context, collector_cls)
                for game, context in cells
            ]
            for fut in futures:
                worker_collector = fut.result()
                self.collector.merge(worker_collector)
