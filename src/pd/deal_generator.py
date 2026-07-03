"""Deal generators: strategies for producing the payoff matrix of a single deal.

This module defines the abstract `DealGenerator` base class. Concrete
implementations live in `pd.deal_generators.*`.

The Game calls `generate(...)` before every deal. A generator receives the
two players and the round index; it returns a Deal object with the payoff
matrix filled in. Actions and scores are added later by Deal.execute().

Swap the generator to run experiments with different payoff structures
(classic Axelrod, noisy, asymmetric, round-dependent, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pd.deal import Deal

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
