"""Deal: a single episode of the prisoner's dilemma between two players.

A Deal is created by a DealGenerator, executed by a Game, and then kept as
an immutable record in the histories of both players and of the Game itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pd.player import Player


class Action(Enum):
    """A player's choice in a deal."""

    COOPERATE = "cooperate"
    DEFECT = "defect"


@dataclass(frozen=True, slots=True)
class DealPayoff:
    """The 8 numbers that fully specify a (possibly asymmetric) deal.

    Naming convention: `payoff_<p1><p2>_<who>` where <p1><p2> are the actions
    of player 1 and player 2 ('c' = cooperate, 'd' = defect), and <who>
    is which player receives the payoff ('1' or '2').

    So `payoff_cd_1` = what player 1 gets when player 1 cooperates and
    player 2 defects (the classic "sucker" payoff for player 1).
    """

    payoff_cc_1: float
    payoff_cc_2: float
    payoff_cd_1: float
    payoff_cd_2: float
    payoff_dc_1: float
    payoff_dc_2: float
    payoff_dd_1: float
    payoff_dd_2: float

    def resolve(self, a1: Action, a2: Action) -> tuple[float, float]:
        """Return (score_for_player_1, score_for_player_2) given both actions."""
        match (a1, a2):
            case (Action.COOPERATE, Action.COOPERATE):
                return self.payoff_cc_1, self.payoff_cc_2
            case (Action.COOPERATE, Action.DEFECT):
                return self.payoff_cd_1, self.payoff_cd_2
            case (Action.DEFECT, Action.COOPERATE):
                return self.payoff_dc_1, self.payoff_dc_2
            case (Action.DEFECT, Action.DEFECT):
                return self.payoff_dd_1, self.payoff_dd_2


@dataclass(slots=True)
class Deal:
    """A single prisoner's dilemma episode.

    Before execution: knows the two players and the payoff matrix.
    After execution: also knows the chosen actions and the resulting scores.

    A Deal is executed exactly once. It enforces simultaneous choice: both
    players' `do_deal` methods are called before either action is revealed
    or written into any history.
    """

    player_1: "Player"
    player_2: "Player"
    payoff: DealPayoff
    round_index: int  # which turn-based round this deal belongs to

    # filled in by execute()
    action_1: Action | None = None
    action_2: Action | None = None
    score_1: float | None = None
    score_2: float | None = None
    executed: bool = False

    def execute(self) -> None:
        """Ask both players for their actions simultaneously, then score.

        "Simultaneously" here means: neither player's `decide` sees the
        other's decision for this deal. We collect both choices first, only
        then compute scores and append to histories.

        Both players are consulted via `Player.decide`, not `Player.do_deal`
        directly, so the base-class chaos coin (`Player.chaos`) is applied
        transparently before the subclass strategy runs.
        """
        if self.executed:
            raise RuntimeError("Deal already executed")

        # Collect both decisions before revealing anything.
        # Each player sees only its own perspective of the deal (opponent ref,
        # payoff from its own point of view, round index) -- see Player.decide.
        a1 = self.player_1.decide(
            opponent=self.player_2,
            payoff=self.payoff,
            self_is_player_1=True,
            round_index=self.round_index,
        )
        a2 = self.player_2.decide(
            opponent=self.player_1,
            payoff=self.payoff,
            self_is_player_1=False,
            round_index=self.round_index,
        )

        if not isinstance(a1, Action) or not isinstance(a2, Action):
            raise TypeError("Player.decide must return an Action")

        s1, s2 = self.payoff.resolve(a1, a2)

        self.action_1 = a1
        self.action_2 = a2
        self.score_1 = s1
        self.score_2 = s2
        self.executed = True

        # Only now write to per-player histories.
        self.player_1._record_deal(opponent=self.player_2, deal=self)
        self.player_2._record_deal(opponent=self.player_1, deal=self)
