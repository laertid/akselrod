"""Players: the actors that decide how to act in each deal.

This module defines the abstract `Player` base class. Concrete strategy
implementations live in `pd.players.*`.

A Player has:
  - a class-level `name()` static method identifying the strategy type;
  - a per-instance `player_id` assigned by the Game when the player is registered;
  - a reference to its Game (so it can look up total round count, etc.);
  - a history of every deal it has participated in, plus a per-opponent index;
  - an optional `chaos` probability of picking a uniformly random action on
    any given deal, applied by the base class before the subclass strategy
    is consulted.

Subclasses implement `do_deal(...)` to choose an Action for a given deal.
They have full information available: their own history, the opponent object
(and via it, the opponent's history), the current round index, and the game
reference (for e.g. total number of rounds).

The base class exposes `decide(...)` as the entry point Deal calls. `decide`
rolls the chaos coin first; on "chaos" it returns a uniformly random Action
without consulting the subclass, otherwise it delegates to `do_deal`. This
keeps chaos orthogonal to the strategy: every Player subclass gets a noisy
variant for free without changing its `do_deal` implementation.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pd.deal import Action, DealPayoff

if TYPE_CHECKING:
    from pd.deal import Deal
    from pd.game import Game


class Player(ABC):
    """Abstract base class for all strategies."""

    def __init__(
        self,
        chaos: float = 0.0,
        chaos_rng: random.Random | None = None,
    ) -> None:
        """Initialize the base player.

        Args:
            chaos: probability in [0.0, 1.0] of ignoring the subclass
                strategy on any given deal and returning a uniformly
                random Action (50/50 COOPERATE / DEFECT). Default 0.0
                (no chaos -- the subclass strategy is always used).
            chaos_rng: dedicated `random.Random` used only for chaos
                decisions. Keeping it separate from any strategy-owned
                RNG (e.g. RandomDefect's own stream) and from the
                game-level RNG (used for pair shuffling) means changing
                `chaos` doesn't shift any other pseudorandom sequence.
                If `None` and `chaos > 0`, a fresh nondeterministic
                `random.Random()` is created lazily.
        """
        if not 0.0 <= chaos <= 1.0:
            raise ValueError(f"chaos must be in [0.0, 1.0], got {chaos}")
        self.chaos = chaos
        self._chaos_rng = chaos_rng

        # Assigned by Game.register_player(); None until then.
        self.player_id: int | None = None
        self.game: "Game | None" = None

        # Full chronological history of deals this player participated in.
        self._history: list["Deal"] = []
        # Per-opponent index into that history, in chronological order.
        self._history_by_opponent: dict[int, list["Deal"]] = {}

    # ---- identity ---------------------------------------------------------

    @staticmethod
    @abstractmethod
    def name() -> str:
        """Human-readable strategy name. Distinct per Player subclass."""
        ...

    # ---- lifecycle hooks called by Game ----------------------------------

    def bind_to_game(self, game: "Game", player_id: int) -> None:
        """Called once by Game before play starts. Overridable if a strategy
        wants to precompute anything from `game.total_rounds` or the roster."""
        if self.game is not None:
            raise RuntimeError(f"Player {self.name()} already bound to a game")
        self.game = game
        self.player_id = player_id

    # ---- history access ---------------------------------------------------

    @property
    def history(self) -> list["Deal"]:
        """All deals this player has played, in chronological order."""
        return self._history

    def history_with(self, opponent: "Player") -> list["Deal"]:
        """All deals this player has played against a specific opponent."""
        if opponent.player_id is None:
            raise RuntimeError("Opponent has no player_id (not bound to a game)")
        return self._history_by_opponent.get(opponent.player_id, [])

    def total_score(self) -> float:
        """Sum of scores this player has earned across all deals so far."""
        total = 0.0
        for deal in self._history:
            total += deal.score_1 if deal.player_1 is self else deal.score_2
        return total

    def _record_deal(self, opponent: "Player", deal: "Deal") -> None:
        """Internal: called by Deal.execute() after both actions are chosen."""
        assert opponent.player_id is not None
        self._history.append(deal)
        self._history_by_opponent.setdefault(opponent.player_id, []).append(deal)

    # ---- decision --------------------------------------------------------

    def decide(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        """Choose an Action for the current deal, applying chaos.

        This is what `Deal.execute()` calls. With probability `self.chaos`,
        return a uniformly random Action (50/50 COOPERATE / DEFECT) drawn
        from `self._chaos_rng` without consulting the subclass. Otherwise
        delegate to `do_deal`.

        Subclasses should NOT override `decide`. They should override
        `do_deal`.
        """
        if self.chaos > 0.0:
            if self._chaos_rng is None:
                # Lazily create a fresh nondeterministic RNG. Passing an
                # explicit `chaos_rng` at construction time is preferred
                # for reproducibility.
                self._chaos_rng = random.Random()
            if self._chaos_rng.random() < self.chaos:
                return (
                    Action.COOPERATE
                    if self._chaos_rng.random() < 0.5
                    else Action.DEFECT
                )
        return self.do_deal(opponent, payoff, self_is_player_1, round_index)

    @abstractmethod
    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        """Decide how to act in the current deal, ignoring chaos.

        Called by `Player.decide` after the chaos coin has been rolled.
        The player may inspect its own history, the opponent's history,
        the payoff matrix (note: perspective depends on `self_is_player_1`),
        the round index, and `self.game` for global info like total rounds.

        Subclasses implementing new strategies override this method.
        """
        ...
