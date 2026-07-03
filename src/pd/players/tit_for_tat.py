"""TitForTat: Anatol Rapoport's winning strategy from Axelrod's 1980 tournaments.

Rules:
  1. Cooperate on the first encounter with a given opponent.
  2. On every subsequent encounter, mirror what that opponent did to you
     in your most recent deal against them.

Notes on scope:
- The strategy looks only at pairwise history with the current opponent
  (not the opponent's behavior against third parties). "Repay in kind"
  is deliberately local.
- The payoff matrix is not consulted. TFT reacts to actions, not to
  specific temptation/reward values -- which is why it's robust across
  different DealGenerator variants.
"""

from __future__ import annotations

from pd.deal import Action, DealPayoff
from pd.player import Player


class TitForTat(Player):
    """Cooperate on the first move, then copy the opponent's previous move."""

    @staticmethod
    def name() -> str:
        return "TitForTat"

    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        prior = self.history_with(opponent)
        if not prior:
            # First encounter with this opponent -> start nice.
            return Action.COOPERATE

        # In the most recent deal against this opponent, figure out which
        # action the *opponent* played (which side of the deal they were on)
        # and mirror it.
        last = prior[-1]
        opponent_last_action = (
            last.action_2 if last.player_1 is self else last.action_1
        )
        assert opponent_last_action is not None, (
            "Deal in history must have been executed"
        )
        return opponent_last_action
