"""Players: the actors that decide how to act in each deal.

A Player has:
  - a class-level `name()` static method identifying the strategy type;
  - a per-instance `player_id` assigned by the Game when the player is registered;
  - a reference to its Game (so it can look up total round count, etc.);
  - a history of every deal it has participated in, plus a per-opponent index.

Subclasses implement `do_deal(...)` to choose an Action for a given deal.
They have full information available: their own history, the opponent object
(and via it, the opponent's history), the current round index, and the game
reference (for e.g. total number of rounds).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pd.deal import Action, DealPayoff

if TYPE_CHECKING:
    from pd.deal import Deal
    from pd.game import Game


class Player(ABC):
    """Abstract base class for all strategies."""

    def __init__(self) -> None:
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

    @abstractmethod
    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        """Decide how to act in the current deal.

        Called by Deal.execute() before any action is revealed. The player
        may inspect its own history, the opponent's history, the payoff
        matrix (note: perspective depends on `self_is_player_1`), the round
        index, and `self.game` for global info like total rounds.
        """
        ...


class AlwaysCooperate(Player):
    """Trivial baseline: cooperate unconditionally."""

    @staticmethod
    def name() -> str:
        return "AlwaysCooperate"

    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        return Action.COOPERATE
