"""Deal generators: strategies for producing the payoff matrix of a single deal.

The Game calls `generate(...)` before every deal. A generator receives the
two players and the round index; it returns a Deal object with the payoff
matrix filled in. Actions and scores are added later by Deal.execute().

Swap the generator to run experiments with different payoff structures
(classic Axelrod, noisy, asymmetric, round-dependent, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pd.deal import Deal, DealPayoff

if TYPE_CHECKING:
    from pd.player import Player


class DealGenerator(ABC):
    """Abstract base class for deal generators."""

    @abstractmethod
    def generate(
        self,
        player_1: "Player",
        player_2: "Player",
        round_index: int,
    ) -> Deal:
        """Produce a fresh, un-executed Deal for these two players."""
        ...


class ClassicAxelrodGenerator(DealGenerator):
    """The canonical symmetric payoff matrix from Axelrod's tournaments.

    Defaults: T=5, R=3, P=1, S=0 (temptation, reward, punishment, sucker).
    Satisfies T > R > P > S and 2R > T + S (the two conditions that make
    it a proper iterated prisoner's dilemma).
    """

    def __init__(
        self,
        temptation: float = 5.0,
        reward: float = 3.0,
        punishment: float = 1.0,
        sucker: float = 0.0,
    ) -> None:
        if not (temptation > reward > punishment > sucker):
            raise ValueError("Require T > R > P > S")
        if not (2 * reward > temptation + sucker):
            raise ValueError("Require 2R > T + S (else alternating C/D dominates)")
        self.T = temptation
        self.R = reward
        self.P = punishment
        self.S = sucker

    def generate(
        self,
        player_1: "Player",
        player_2: "Player",
        round_index: int,
    ) -> Deal:
        payoff = DealPayoff(
            payoff_cc_1=self.R, payoff_cc_2=self.R,
            payoff_cd_1=self.S, payoff_cd_2=self.T,
            payoff_dc_1=self.T, payoff_dc_2=self.S,
            payoff_dd_1=self.P, payoff_dd_2=self.P,
        )
        return Deal(
            player_1=player_1,
            player_2=player_2,
            payoff=payoff,
            round_index=round_index,
        )
