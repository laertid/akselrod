"""Collector: abstract data-mining hook called once per finished game.

Collectors are stateful sinks. A concrete Collector accumulates whatever
it wants (rows, aggregates, per-strategy tallies, ...) in its own
attributes. `Multigame.run()` calls `collector.collect(game, context)`
after each game finishes, and never inspects the return value.

The `context` dict is opaque to the framework: it is whatever the caller
attached to a specific (game, context) cell (e.g. seed, strategy label,
grid coordinates, replicate index). The Collector decides how to use it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pd.game import Game


class Collector(ABC):
    """Base class for game-finish data collectors.

    Concrete subclasses store their results in their own state and expose
    them via ordinary attributes / methods -- there is no framework-level
    aggregation.
    """

    @abstractmethod
    def collect(self, game: Game, context: dict) -> None:
        """Called once, after `game.play()` has completed.

        Implementations must not mutate `game` or `context`; they should
        only read from them and write to their own state.
        """
        raise NotImplementedError

    def merge(self, other: "Collector") -> None:
        """Merge another collector's state into this one.

        Used by `Multigame.run_parallel(...)`: each worker process
        instantiates a fresh collector of the same class, calls
        `collect(...)` on the games it played, and sends the resulting
        object back to the parent, where the parent's collector merges
        each worker collector via this method.

        The default raises `NotImplementedError`; concrete collectors
        that want to be usable with `run_parallel` must override.
        Sequential `Multigame.run()` never calls `merge`, so collectors
        that only run sequentially can leave it unimplemented.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement merge(); it cannot be "
            "used with Multigame.run_parallel. Override Collector.merge to "
            "combine two instances of this collector."
        )
