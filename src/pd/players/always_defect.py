"""AlwaysDefect: the pessimistic baseline that defects unconditionally."""

from __future__ import annotations

from pd.deal import Action, DealPayoff
from pd.player import Player


class AlwaysDefect(Player):
    """Defect on every deal, regardless of context."""

    @staticmethod
    def name() -> str:
        return "AlwaysDefect"

    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        return Action.DEFECT
