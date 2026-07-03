"""Minimal example: four AlwaysCooperate players run for 10 rounds."""

from pd import AlwaysCooperate, ClassicAxelrodGenerator, Game, set_seed


def main() -> None:
    set_seed(42)
    players = [AlwaysCooperate() for _ in range(4)]
    game = Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=players,
        total_rounds=10,
    )
    game.play()

    print(f"Total deals played: {len(game.history)}")
    print("Leaderboard:")
    for player, score in game.leaderboard():
        print(f"  #{player.player_id} {player.name():>20}  score={score}")


if __name__ == "__main__":
    main()
