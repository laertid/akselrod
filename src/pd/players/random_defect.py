"""RandomDefect: defects independently on each deal with a fixed probability.

Memoryless. Ignores the opponent, the payoff matrix, and the round index.
Useful as a noise floor: at p=0 it is AlwaysCooperate, at p=1 it is
AlwaysDefect, and in between it is a Bernoulli process.
"""

from __future__ import annotations

import random

from pd.deal import Action, DealPayoff
from pd.player import Player


class RandomDefect(Player):
    """Defect with probability `p`, cooperate with probability `1 - p`."""

    def __init__(self, p: float, rng: random.Random) -> None:
        super().__init__()
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0, 1], got {p}")
        self.p = p
        self._rng = rng

    @staticmethod
    def name() -> str:
        return "RandomDefect"

    def do_deal(
        self,
        opponent: "Player",
        payoff: DealPayoff,
        self_is_player_1: bool,
        round_index: int,
    ) -> Action:
        return Action.DEFECT if self._rng.random() < self.p else Action.COOPERATE
