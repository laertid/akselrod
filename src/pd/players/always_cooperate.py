"""AlwaysCooperate: trivial baseline strategy that cooperates unconditionally."""

from __future__ import annotations

from pd.deal import Action, DealPayoff
from pd.player import Player


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
