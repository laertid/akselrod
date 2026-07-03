"""Tit-for-Tat against a mixed field.

Reproduces the flavor of Axelrod's tournament: TFT ends up looking modest
per-pair, but its total across the field is competitive because it never
loses badly.
"""

from pd import (
    Action,
    AlwaysCooperate,
    ClassicAxelrodGenerator,
    Game,
    Player,
    TitForTat,
    set_seed,
)


class AlwaysDefect(Player):
    @staticmethod
    def name() -> str:
        return "AlwaysDefect"

    def do_deal(self, opponent, payoff, self_is_player_1, round_index):
        return Action.DEFECT


def main() -> None:
    set_seed(42)
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
    )
    game.play()

    print(f"Total deals played: {len(game.history)}")
    print("Leaderboard:")
    for player, score in game.leaderboard():
        print(f"  #{player.player_id} {player.name():>16}  score={score}")


if __name__ == "__main__":
    main()
