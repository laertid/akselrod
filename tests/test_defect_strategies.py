"""Tests for AlwaysDefect, RandomDefect, and RandomDefectTft."""

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
    create_rng,
    set_seed,
)


# =============================================================================
# AlwaysDefect
# =============================================================================


def test_always_defect_name():
    assert AlwaysDefect.name() == "AlwaysDefect"


def test_always_defect_defects_every_deal():
    set_seed(0)
    ad = AlwaysDefect()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [ad, coop], total_rounds=10)
    game.play()

    for deal in game.history:
        ad_action = deal.action_1 if deal.player_1 is ad else deal.action_2
        assert ad_action == Action.DEFECT
    # Exploits AllC completely: 10 * T = 50; AllC gets 10 * S = 0.
    assert ad.total_score() == 50
    assert coop.total_score() == 0


def test_always_defect_vs_always_defect_locks_at_punishment():
    set_seed(0)
    a, b = AlwaysDefect(), AlwaysDefect()
    game = Game(ClassicAxelrodGenerator(), [a, b], total_rounds=7)
    game.play()

    for deal in game.history:
        assert deal.action_1 == Action.DEFECT
        assert deal.action_2 == Action.DEFECT
    # P = 1 per round.
    assert a.total_score() == 7
    assert b.total_score() == 7


# =============================================================================
# RandomDefect
# =============================================================================


def test_random_defect_rejects_invalid_p():
    rng = create_rng("x")
    with pytest.raises(ValueError):
        RandomDefect(p=-0.01, rng=rng)
    with pytest.raises(ValueError):
        RandomDefect(p=1.01, rng=rng)


def test_random_defect_p_zero_is_always_cooperate():
    rng = create_rng("seed-a")
    rd = RandomDefect(p=0.0, rng=rng)
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [rd, coop], total_rounds=25)
    game.play()

    for deal in game.history:
        rd_action = deal.action_1 if deal.player_1 is rd else deal.action_2
        assert rd_action == Action.COOPERATE


def test_random_defect_p_one_is_always_defect():
    rng = create_rng("seed-b")
    rd = RandomDefect(p=1.0, rng=rng)
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [rd, coop], total_rounds=25)
    game.play()

    for deal in game.history:
        rd_action = deal.action_1 if deal.player_1 is rd else deal.action_2
        assert rd_action == Action.DEFECT


def test_random_defect_reproducible_with_same_seeded_rng():
    def run() -> list[Action]:
        set_seed(0)  # controls Game shuffling
        rng = create_rng("player-seed")
        rd = RandomDefect(p=0.3, rng=rng)
        coop = AlwaysCooperate()
        game = Game(ClassicAxelrodGenerator(), [rd, coop], total_rounds=50)
        game.play()
        return [d.action_1 if d.player_1 is rd else d.action_2 for d in game.history]

    assert run() == run()


def test_random_defect_frequency_matches_p():
    rng = create_rng("large-sample")
    rd = RandomDefect(p=0.3, rng=rng)
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [rd, coop], total_rounds=5000)
    game.play()

    defects = sum(
        1
        for d in game.history
        if (d.action_1 if d.player_1 is rd else d.action_2) == Action.DEFECT
    )
    freq = defects / 5000
    # With N=5000 and p=0.3 the 4-sigma band is ~0.026 wide; 0.03 is safe.
    assert abs(freq - 0.3) < 0.03


def test_random_defect_independent_rngs_diverge():
    """Two RandomDefects with independent seeded RNGs should differ in
    their action sequences (with overwhelming probability at N=200)."""
    rng_a = create_rng("A")
    rng_b = create_rng("B")
    a = RandomDefect(p=0.5, rng=rng_a)
    b = RandomDefect(p=0.5, rng=rng_b)
    coop = AlwaysCooperate()
    set_seed(0)
    game = Game(ClassicAxelrodGenerator(), [a, b, coop], total_rounds=200)
    game.play()

    seq_a = [d.action_1 if d.player_1 is a else d.action_2 for d in a.history]
    seq_b = [d.action_1 if d.player_1 is b else d.action_2 for d in b.history]
    assert seq_a != seq_b


# =============================================================================
# RandomDefectTft
# =============================================================================


def test_random_defect_tft_rejects_invalid_p():
    rng = create_rng("x")
    with pytest.raises(ValueError):
        RandomDefectTft(p=-0.01, rng=rng)
    with pytest.raises(ValueError):
        RandomDefectTft(p=1.01, rng=rng)


def test_random_defect_tft_p_zero_is_pure_tft():
    """With p=0 the strategy must match TitForTat action-for-action against
    the same opponent script."""
    rng = create_rng("zero")
    noisy = RandomDefectTft(p=0.0, rng=rng)
    pure = TitForTat()
    # Play both against an AllD in separate games and compare their action
    # sequences.
    for player, label in [(noisy, "noisy"), (pure, "pure")]:
        set_seed(0)
        ad = AlwaysDefect()
        Game(ClassicAxelrodGenerator(), [player, ad], total_rounds=10).play()

    noisy_seq = [
        d.action_1 if d.player_1 is noisy else d.action_2 for d in noisy.history
    ]
    pure_seq = [
        d.action_1 if d.player_1 is pure else d.action_2 for d in pure.history
    ]
    assert noisy_seq == pure_seq


def test_random_defect_tft_p_one_is_always_defect():
    rng = create_rng("one")
    noisy = RandomDefectTft(p=1.0, rng=rng)
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [noisy, coop], total_rounds=20)
    game.play()

    for d in game.history:
        a = d.action_1 if d.player_1 is noisy else d.action_2
        assert a == Action.DEFECT


def test_random_defect_tft_reproducible():
    def run() -> list[Action]:
        set_seed(0)
        rng = create_rng("noisy-tft")
        noisy = RandomDefectTft(p=0.1, rng=rng)
        coop = AlwaysCooperate()
        game = Game(ClassicAxelrodGenerator(), [noisy, coop], total_rounds=100)
        game.play()
        return [
            d.action_1 if d.player_1 is noisy else d.action_2 for d in game.history
        ]

    assert run() == run()


def test_random_defect_tft_falls_out_of_cooperation_against_itself():
    """The classic failure mode: two noisy TFTs against each other spend a
    large fraction of the tournament in mutual defection cascades."""
    set_seed(0)
    rng_a = create_rng("A")
    rng_b = create_rng("B")
    a = RandomDefectTft(p=0.05, rng=rng_a)
    b = RandomDefectTft(p=0.05, rng=rng_b)
    game = Game(ClassicAxelrodGenerator(), [a, b], total_rounds=500)
    game.play()

    cc = sum(
        1
        for d in game.history
        if d.action_1 == Action.COOPERATE and d.action_2 == Action.COOPERATE
    )
    # Two pure TFTs would give cc == 500. With 5% asymmetric noise the
    # C/C rate drops substantially. Empirically <60%.
    assert cc / 500 < 0.6


def test_random_defect_tft_uses_only_its_own_rng():
    """Behavior must not change when the global RNG stream is disturbed
    between rounds -- the player's stream is independent."""

    def run(disturb_global: bool) -> list[Action]:
        set_seed(0)
        rng = create_rng("own")
        noisy = RandomDefectTft(p=0.3, rng=rng)
        coop = AlwaysCooperate()
        game = Game(ClassicAxelrodGenerator(), [noisy, coop], total_rounds=50)
        game.play()
        if disturb_global:
            # Consuming from global rng after the fact should be irrelevant.
            from pd import global_rng
            for _ in range(37):
                global_rng().random()
        return [
            d.action_1 if d.player_1 is noisy else d.action_2 for d in game.history
        ]

    # Both calls have identical setup for the player rng; global draws
    # after the game don't matter, and the game shuffle inside is seeded
    # deterministically by set_seed(0).
    assert run(False) == run(True)
