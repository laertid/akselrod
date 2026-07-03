"""Small tournament showing how defection noise disrupts cooperation.

Two TitForTat players usually lock into mutual cooperation. Replacing them
with RandomDefectTft(p=0.05) breaks the cooperation cascade, and predictable
defectors profit.
"""

import random

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Game,
    RandomDefect,
    RandomDefectTft,
    TitForTat,
)


def main() -> None:
    players = [
        TitForTat(),
        TitForTat(),
        AlwaysCooperate(),
        AlwaysDefect(),
        RandomDefect(p=0.5, rng=random.Random("rd")),
        RandomDefectTft(p=0.05, rng=random.Random("noisy-tft")),
    ]
    game = Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=players,
        total_rounds=200,
        rng=random.Random(42),
    )
    game.play()

    print(f"Total deals played: {len(game.history)}")
    print("Leaderboard:")
    for player, score in game.leaderboard():
        print(f"  #{player.player_id} {player.name():>18}  score={score}")


if __name__ == "__main__":
    main()
