"""Tit-for-Tat against a mixed field.

Reproduces the flavor of Axelrod's tournament: TFT ends up looking modest
per-pair, but its total across the field is competitive because it never
loses badly.
"""

import random

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Game,
    TitForTat,
)


def main() -> None:
    players = [
        TitForTat(),
        AlwaysCooperate(),
        AlwaysCooperate(),
        AlwaysDefect(),
    ]
    game = Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=players,
        total_rounds=100,
        rng=random.Random(42),
    )
    game.play()

    print(f"Total deals played: {len(game.history)}")
    print("Leaderboard:")
    for player, score in game.leaderboard():
        print(f"  #{player.player_id} {player.name():>16}  score={score}")


if __name__ == "__main__":
    main()
