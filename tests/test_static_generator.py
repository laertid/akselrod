"""Tests for StaticGenerator."""

from __future__ import annotations

import random

import pytest

from pd import (
    Action,
    AlwaysCooperate,
    AlwaysDefect,
    DealPayoff,
    Game,
    StaticGenerator,
    TitForTat,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _classic_payoff() -> DealPayoff:
    """T=5, R=3, P=1, S=0 -- same numbers as ClassicAxelrodGenerator."""
    return DealPayoff(
        payoff_cc_1=3.0, payoff_cc_2=3.0,
        payoff_cd_1=0.0, payoff_cd_2=5.0,
        payoff_dc_1=5.0, payoff_dc_2=0.0,
        payoff_dd_1=1.0, payoff_dd_2=1.0,
    )


def _asymmetric_payoff() -> DealPayoff:
    """Deliberately asymmetric: player 1 always gets more than player 2."""
    return DealPayoff(
        payoff_cc_1=10.0, payoff_cc_2=1.0,
        payoff_cd_1=8.0, payoff_cd_2=2.0,
        payoff_dc_1=9.0, payoff_dc_2=3.0,
        payoff_dd_1=7.0, payoff_dd_2=4.0,
    )


# ---------------------------------------------------------------------------
# Payoff propagation
# ---------------------------------------------------------------------------


def test_generate_returns_deal_with_supplied_payoff():
    payoff = _classic_payoff()
    gen = StaticGenerator(payoff)

    p1 = AlwaysCooperate()
    p2 = AlwaysDefect()
    deal = gen.generate(p1, p2, round_index=7)

    assert deal.player_1 is p1
    assert deal.player_2 is p2
    assert deal.round_index == 7
    assert deal.payoff == payoff


def test_generate_preserves_asymmetric_payoff():
    payoff = _asymmetric_payoff()
    gen = StaticGenerator(payoff)
    deal = gen.generate(AlwaysCooperate(), AlwaysDefect(), round_index=0)

    assert deal.payoff.payoff_cc_1 == 10.0
    assert deal.payoff.payoff_cc_2 == 1.0
    assert deal.payoff.payoff_dc_1 == 9.0
    assert deal.payoff.payoff_dc_2 == 3.0


# ---------------------------------------------------------------------------
# Fresh copy guarantee
# ---------------------------------------------------------------------------


def test_generate_returns_a_fresh_payoff_each_call():
    payoff = _classic_payoff()
    gen = StaticGenerator(payoff)

    deal_a = gen.generate(AlwaysCooperate(), AlwaysDefect(), round_index=0)
    deal_b = gen.generate(AlwaysCooperate(), AlwaysDefect(), round_index=1)

    # Different DealPayoff instances...
    assert deal_a.payoff is not deal_b.payoff
    assert deal_a.payoff is not payoff
    assert deal_b.payoff is not payoff
    # ...with identical fields.
    assert deal_a.payoff == deal_b.payoff == payoff


# ---------------------------------------------------------------------------
# End-to-end: Game plays through unchanged
# ---------------------------------------------------------------------------


def test_game_with_static_generator_reproduces_classic_axelrod_scores():
    """With T=5, R=3, P=1, S=0 the static generator should produce the
    exact same per-round scores as ClassicAxelrodGenerator on the same
    line-up (AllC vs AllD -> 0 and T per round)."""
    payoff = _classic_payoff()
    game = Game(
        deal_generator=StaticGenerator(payoff),
        players=[AlwaysCooperate(), AlwaysDefect()],
        total_rounds=10,
        rng=random.Random(1),
    )
    game.play()

    scores = game.scores()
    # AllC gets S=0 every round, AllD gets T=5 every round.
    assert scores == {0: 0.0, 1: 50.0}


def test_game_with_asymmetric_static_payoff_end_to_end():
    """Under _asymmetric_payoff, TFT vs AlwaysDefect for 5 rounds:
    round 0: TFT cooperates, AllD defects -> CD -> (8, 2)
    rounds 1..4: TFT defects, AllD defects -> DD -> (7, 4)
    Totals: TFT = 8 + 4*7 = 36; AllD = 2 + 4*4 = 18."""
    payoff = _asymmetric_payoff()
    game = Game(
        deal_generator=StaticGenerator(payoff),
        players=[TitForTat(), AlwaysDefect()],
        total_rounds=5,
        rng=random.Random(1),
    )
    game.play()

    assert game.scores() == {0: 36.0, 1: 18.0}


def test_game_history_records_the_static_payoff():
    payoff = _classic_payoff()
    game = Game(
        deal_generator=StaticGenerator(payoff),
        players=[AlwaysCooperate(), AlwaysCooperate()],
        total_rounds=3,
        rng=random.Random(1),
    )
    game.play()

    assert len(game.history) == 3
    for deal in game.history:
        assert deal.payoff == payoff
        # Both cooperators -> both get R=3.
        assert deal.action_1 == Action.COOPERATE
        assert deal.action_2 == Action.COOPERATE
        assert deal.score_1 == 3.0
        assert deal.score_2 == 3.0


# ---------------------------------------------------------------------------
# Degenerate matrices are allowed
# ---------------------------------------------------------------------------


def test_static_generator_accepts_zero_payoff():
    """Unlike ClassicAxelrodGenerator, StaticGenerator does not enforce
    T > R > P > S. All-zero payoffs are allowed."""
    payoff = DealPayoff(
        payoff_cc_1=0.0, payoff_cc_2=0.0,
        payoff_cd_1=0.0, payoff_cd_2=0.0,
        payoff_dc_1=0.0, payoff_dc_2=0.0,
        payoff_dd_1=0.0, payoff_dd_2=0.0,
    )
    gen = StaticGenerator(payoff)
    deal = gen.generate(AlwaysCooperate(), AlwaysDefect(), round_index=0)
    assert deal.payoff == payoff
