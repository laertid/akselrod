"""Game: orchestrates a turn-based tournament between a set of players.

Structure:
  - The Game is constructed with a DealGenerator, a list of players, and a
    total number of rounds.
  - Each player is bound to the Game and assigned a unique player_id.
  - In each round, every unordered pair of distinct players plays exactly
    one deal (players do NOT play against themselves). The order of pairs
    within a round is shuffled via the global RNG for fairness.
  - All executed deals are kept in `Game.history` in the order they were played,
    so downstream analysis (e.g. converting to a DataFrame) is straightforward.
"""

from __future__ import annotations

import itertools

from pd.deal import Deal
from pd.deal_generator import DealGenerator
from pd.player import Player
from pd.rng import get_rng


class Game:
    """A turn-based iterated prisoner's dilemma tournament."""

    def __init__(
        self,
        deal_generator: DealGenerator,
        players: list[Player],
        total_rounds: int,
    ) -> None:
        if total_rounds < 1:
            raise ValueError("total_rounds must be >= 1")
        if len(players) < 2:
            raise ValueError("need at least 2 players")

        self.deal_generator = deal_generator
        self.players: list[Player] = list(players)
        self.total_rounds = total_rounds

        # Bind every player to this game with a stable unique id.
        for idx, player in enumerate(self.players):
            player.bind_to_game(self, player_id=idx)

        # Full chronological log of executed deals.
        self.history: list[Deal] = []

    def play(self) -> None:
        """Run all rounds. After this returns, `self.history` and each
        player's history are populated."""
        pairs = list(itertools.combinations(self.players, 2))
        rng = get_rng()

        for round_index in range(self.total_rounds):
            # Shuffle pair order each round so no pair has a systematic
            # first/last-mover advantage across the tournament.
            round_pairs = pairs[:]
            rng.shuffle(round_pairs)

            for p1, p2 in round_pairs:
                deal = self.deal_generator.generate(p1, p2, round_index)
                deal.execute()
                self.history.append(deal)

    # ---- convenience accessors for analysis ------------------------------

    def scores(self) -> dict[int, float]:
        """Total score per player_id."""
        return {p.player_id: p.total_score() for p in self.players}  # type: ignore[misc]

    def leaderboard(self) -> list[tuple[Player, float]]:
        """Players sorted by total score, descending."""
        return sorted(
            ((p, p.total_score()) for p in self.players),
            key=lambda pair: pair[1],
            reverse=True,
        )
