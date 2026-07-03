"""RandomDefectTft: Tit-for-Tat with asymmetric defection noise.

Rule:
  1. Compute the pure TFT action (cooperate on first encounter with an
     opponent, otherwise mirror that opponent's last action against us).
  2. With probability `p`, override the result to defect.
  3. Otherwise, play the TFT action as-is.

The noise is asymmetric: it only pushes toward D, never toward C. Two
copies of this strategy playing each other tend to fall out of mutual
cooperation and into long punishment cascades -- the classic weakness of
TFT under noise.
"""

from __future__ import annotations

import random

from pd.deal import Action, DealPayoff
from pd.player import Player


class RandomDefectTft(Player):
    """Tit-for-Tat, but defect anyway with probability `p` on each move."""

    def __init__(self, p: float, rng: random.Random) -> None:
        super().__init__()
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0, 1], got {p}")
        self.p = p
        self._rng = rng

    @staticmethod
    def name() -> str:
        return "RandomDefectTft"

    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        # Random override first, so we always consume one rng draw per
        # deal. This keeps behavior reproducible even when the pairwise
        # history is short-circuited by the noise.
        forced_defect = self._rng.random() < self.p

        prior = self.history_with(opponent)
        if not prior:
            tft_action = Action.COOPERATE
        else:
            last = prior[-1]
            opponent_last_action = (
                last.action_2 if last.player_1 is self else last.action_1
            )
            assert opponent_last_action is not None
            tft_action = opponent_last_action

        return Action.DEFECT if forced_defect else tft_action
