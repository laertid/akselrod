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
