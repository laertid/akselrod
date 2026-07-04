"""StaticGenerator: emits deals with a fixed, caller-supplied payoff matrix."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pd.deal import Deal, DealPayoff
from pd.deal_generator import DealGenerator

if TYPE_CHECKING:
    from pd.player import Player


class StaticGenerator(DealGenerator):
    """Emits deals whose payoff matrix is a fixed `DealPayoff`.

    Unlike `ClassicAxelrodGenerator`, this generator does not enforce the
    T > R > P > S / 2R > T + S inequalities: the caller decides. Handy
    for degenerate scenarios (zero-sum, symmetric, harmless, ...), for
    tests, and for experiments that vary the matrix along a grid axis.

    Every call to `generate(...)` returns a Deal whose `payoff` is a
    fresh `DealPayoff` copy, so downstream mutation (should any ever be
    introduced) can't leak between deals.
    """

    def __init__(self, payoff: DealPayoff) -> None:
        self.payoff = payoff

    def generate(
        self,
        player_1: "Player",
        player_2: "Player",
        round_index: int,
    ) -> Deal:
        # DealPayoff is frozen, so `replace(...)` with no changes produces
        # a distinct instance with identical fields -- the "fresh copy"
        # guarantee is cheap here.
        return Deal(
            player_1=player_1,
            player_2=player_2,
            payoff=replace(self.payoff),
            round_index=round_index,
        )
