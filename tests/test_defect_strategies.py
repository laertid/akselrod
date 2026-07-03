"""Tests for AlwaysDefect, RandomDefect, and RandomDefectTft."""

import random

import pytest

from pd import (
    Action,
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Game,
    RandomDefect,
    RandomDefectTft,
    TitForTat,
)


def _game_rng(seed: int = 0) -> random.Random:
    """Fresh rng for the Game (shuffles pair order)."""
    return random.Random(seed)


# =============================================================================
# AlwaysDefect
# =============================================================================


def test_always_defect_name():
    assert AlwaysDefect.name() == "AlwaysDefect"


def test_always_defect_defects_every_deal():
    ad = AlwaysDefect()
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [ad, coop], total_rounds=10, rng=_game_rng()
    )
    game.play()

    for deal in game.history:
        ad_action = deal.action_1 if deal.player_1 is ad else deal.action_2
        assert ad_action == Action.DEFECT
    assert ad.total_score() == 50
    assert coop.total_score() == 0


def test_always_defect_vs_always_defect_locks_at_punishment():
    a, b = AlwaysDefect(), AlwaysDefect()
    game = Game(ClassicAxelrodGenerator(), [a, b], total_rounds=7, rng=_game_rng())
    game.play()

    for deal in game.history:
        assert deal.action_1 == Action.DEFECT
        assert deal.action_2 == Action.DEFECT
    assert a.total_score() == 7
    assert b.total_score() == 7


# =============================================================================
# RandomDefect
# =============================================================================


def test_random_defect_rejects_invalid_p():
    rng = random.Random("x")
    with pytest.raises(ValueError):
        RandomDefect(p=-0.01, rng=rng)
    with pytest.raises(ValueError):
        RandomDefect(p=1.01, rng=rng)


def test_random_defect_p_zero_is_always_cooperate():
    rd = RandomDefect(p=0.0, rng=random.Random("seed-a"))
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [rd, coop], total_rounds=25, rng=_game_rng()
    )
    game.play()

    for deal in game.history:
        rd_action = deal.action_1 if deal.player_1 is rd else deal.action_2
        assert rd_action == Action.COOPERATE


def test_random_defect_p_one_is_always_defect():
    rd = RandomDefect(p=1.0, rng=random.Random("seed-b"))
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [rd, coop], total_rounds=25, rng=_game_rng()
    )
    game.play()

    for deal in game.history:
        rd_action = deal.action_1 if deal.player_1 is rd else deal.action_2
        assert rd_action == Action.DEFECT


def test_random_defect_reproducible_with_same_seeded_rng():
    def run() -> list[Action]:
        rd = RandomDefect(p=0.3, rng=random.Random("player-seed"))
        coop = AlwaysCooperate()
        game = Game(
            ClassicAxelrodGenerator(),
            [rd, coop],
            total_rounds=50,
            rng=_game_rng(),
        )
        game.play()
        return [d.action_1 if d.player_1 is rd else d.action_2 for d in game.history]

    assert run() == run()


def test_random_defect_frequency_matches_p():
    rd = RandomDefect(p=0.3, rng=random.Random("large-sample"))
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [rd, coop], total_rounds=5000, rng=_game_rng()
    )
    game.play()

    defects = sum(
        1
        for d in game.history
        if (d.action_1 if d.player_1 is rd else d.action_2) == Action.DEFECT
    )
    freq = defects / 5000
    assert abs(freq - 0.3) < 0.03


def test_random_defect_independent_rngs_diverge():
    a = RandomDefect(p=0.5, rng=random.Random("A"))
    b = RandomDefect(p=0.5, rng=random.Random("B"))
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(),
        [a, b, coop],
        total_rounds=200,
        rng=_game_rng(),
    )
    game.play()

    seq_a = [d.action_1 if d.player_1 is a else d.action_2 for d in a.history]
    seq_b = [d.action_1 if d.player_1 is b else d.action_2 for d in b.history]
    assert seq_a != seq_b


# =============================================================================
# RandomDefectTft
# =============================================================================


def test_random_defect_tft_rejects_invalid_p():
    rng = random.Random("x")
    with pytest.raises(ValueError):
        RandomDefectTft(p=-0.01, rng=rng)
    with pytest.raises(ValueError):
        RandomDefectTft(p=1.01, rng=rng)


def test_random_defect_tft_p_zero_is_pure_tft():
    """With p=0 the strategy must match TitForTat action-for-action against
    the same opponent."""
    noisy = RandomDefectTft(p=0.0, rng=random.Random("zero"))
    pure = TitForTat()
    # Play each in its own game against a fresh AllD.
    for player in (noisy, pure):
        ad = AlwaysDefect()
        Game(
            ClassicAxelrodGenerator(),
            [player, ad],
            total_rounds=10,
            rng=_game_rng(),
        ).play()

    noisy_seq = [
        d.action_1 if d.player_1 is noisy else d.action_2 for d in noisy.history
    ]
    pure_seq = [
        d.action_1 if d.player_1 is pure else d.action_2 for d in pure.history
    ]
    assert noisy_seq == pure_seq


def test_random_defect_tft_p_one_is_always_defect():
    noisy = RandomDefectTft(p=1.0, rng=random.Random("one"))
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [noisy, coop], total_rounds=20, rng=_game_rng()
    )
    game.play()

    for d in game.history:
        a = d.action_1 if d.player_1 is noisy else d.action_2
        assert a == Action.DEFECT


def test_random_defect_tft_reproducible():
    def run() -> list[Action]:
        noisy = RandomDefectTft(p=0.1, rng=random.Random("noisy-tft"))
        coop = AlwaysCooperate()
        game = Game(
            ClassicAxelrodGenerator(),
            [noisy, coop],
            total_rounds=100,
            rng=_game_rng(),
        )
        game.play()
        return [
            d.action_1 if d.player_1 is noisy else d.action_2 for d in game.history
        ]

    assert run() == run()


def test_random_defect_tft_falls_out_of_cooperation_against_itself():
    a = RandomDefectTft(p=0.05, rng=random.Random("A"))
    b = RandomDefectTft(p=0.05, rng=random.Random("B"))
    game = Game(
        ClassicAxelrodGenerator(), [a, b], total_rounds=500, rng=_game_rng()
    )
    game.play()

    cc = sum(
        1
        for d in game.history
        if d.action_1 == Action.COOPERATE and d.action_2 == Action.COOPERATE
    )
    assert cc / 500 < 0.6


def test_random_defect_tft_player_rng_isolated_from_game_rng():
    """Two games with identical player-rng seeds but different game-rng
    seeds still produce identical action sequences from the player, since
    the player's decisions don't depend on which order the game shuffles
    pairs in when there are only two players (only one pair)."""

    def run(game_seed: int) -> list[Action]:
        noisy = RandomDefectTft(p=0.3, rng=random.Random("own"))
        coop = AlwaysCooperate()
        game = Game(
            ClassicAxelrodGenerator(),
            [noisy, coop],
            total_rounds=50,
            rng=random.Random(game_seed),
        )
        game.play()
        return [
            d.action_1 if d.player_1 is noisy else d.action_2 for d in game.history
        ]

    assert run(0) == run(999)
